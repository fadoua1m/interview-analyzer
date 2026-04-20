import logging
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.supabase_client import supabase
from app.schemas.analysis import AnalysisRequest, QuestionInput, Report
from app.analysis_pipeline.pipeline import run_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Analysis"])

_MAX_VIDEO_BYTES       = 500 * 1024 * 1024
_ALLOWED_VIDEO_EXTS    = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".m4v"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_interview_targets(interview_id: str) -> list[str]:
    row = (
        supabase.table("interviews")
        .select("target_softskills")
        .eq("id", interview_id)
        .execute()
    )
    return row.data[0].get("target_softskills") or [] if row.data else []


def _load_report(interview_id: str) -> Report:
    """Fetch and deserialise a stored Report from analysis_results."""
    row = (
        supabase.table("analysis_results")
        .select("*")
        .eq("interview_id", interview_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )
    if not row.data:
        raise HTTPException(404, "No analysis found for this interview")

    data = dict(row.data[0])

    # detected_skills is embedded inside text_metrics jsonb (storage format).
    # Extract it to the top level so model_validate() finds it in the right place.
    text_metrics_raw = data.get("text_metrics") or {}
    if isinstance(text_metrics_raw, dict) and not data.get("detected_skills"):
        # pop mutates a copy of text_metrics_raw — we'll put it back cleaned
        embedded = text_metrics_raw.pop("detected_skills", None) or []
        data["detected_skills"] = embedded
        data["text_metrics"] = text_metrics_raw

    if not data.get("interview_id"):
        data["interview_id"] = interview_id
    if not data.get("generated_at"):
        data["generated_at"] = datetime.now(timezone.utc)

    return Report.model_validate(data)


def _persist_report(report: Report, *, upsert: bool = False) -> None:
    """Persist Report to analysis_results. Raises HTTPException(500) on failure."""
    text_metrics_data = report.text_metrics.model_dump()
    text_metrics_data["detected_skills"] = [
        s.model_dump() for s in (report.detected_skills or [])
    ]

    payload = {
        "interview_id":    report.interview_id,
        "qa_pairs_count":  report.qa_pairs_count,
        "generated_at":    report.generated_at.isoformat(),
        "text_metrics":    text_metrics_data,
        "emotion_metrics": report.emotion_metrics.model_dump(),
        "engagement_metrics": report.engagement_metrics.model_dump(),
        "overall_score":   report.overall_score,
        "decision":        report.decision,
        "decision_reasons": report.decision_reasons,
        "hr_summary":      report.hr_summary,
    }

    try:
        if upsert:
            supabase.table("analysis_results").upsert(
                payload, on_conflict="interview_id"
            ).execute()
        else:
            supabase.table("analysis_results").insert(payload).execute()
        logger.info("[DB] Stored analysis for interview_id=%s", report.interview_id)
    except Exception as exc:
        logger.error("[DB] FAILED to store analysis for %s: %s", report.interview_id, exc)
        raise HTTPException(500, f"Failed to persist analysis results: {exc}") from exc


def _validate_video_upload(video: UploadFile) -> None:
    suffix = Path(video.filename or "").suffix.lower()
    if suffix and suffix not in _ALLOWED_VIDEO_EXTS:
        raise HTTPException(400, f"Unsupported video format '{suffix}'. Allowed: {sorted(_ALLOWED_VIDEO_EXTS)}")
    if video.content_type and not video.content_type.startswith(("video/", "application/octet-stream")):
        raise HTTPException(400, f"Expected a video file, got content-type '{video.content_type}'")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/run", response_model=Report)
def run_analysis_route(payload: AnalysisRequest):
    if not (
        supabase.table("interviews").select("id").eq("id", payload.interview_id).execute()
    ).data:
        raise HTTPException(404, "Interview not found")

    targets   = _get_interview_targets(payload.interview_id)
    questions = [
        QuestionInput(id=q.id, text=q.text, rubric=q.rubric, target_skills=targets)
        for q in payload.questions
    ]

    try:
        report = run_analysis(AnalysisRequest(
            interview_id=    payload.interview_id,
            video_url=       payload.video_url,
            questions=       questions,
            scoring_weights= payload.scoring_weights,
        ))
    except Exception as exc:
        logger.exception("[Analysis] run failed for %s", payload.interview_id)
        raise HTTPException(500, f"Analysis failed: {exc}") from exc

    _persist_report(report, upsert=False)
    return report


@router.post("/run-upload", response_model=Report)
def run_analysis_upload(
    video:        UploadFile = File(...),
    interview_id: str        = Form(...),
):
    if not (
        supabase.table("interviews").select("id").eq("id", interview_id).execute()
    ).data:
        raise HTTPException(404, "Interview not found")

    _validate_video_upload(video)

    questions_row = (
        supabase.table("interview_questions")
        .select("id, question, rubric")
        .eq("interview_id", interview_id)
        .order("order_index", desc=False)
        .execute()
    )
    if not questions_row.data:
        raise HTTPException(400, "This interview has no questions.")

    targets   = _get_interview_targets(interview_id)
    questions = [
        QuestionInput(
            id=           row["id"],
            text=         row["question"],
            rubric=       row.get("rubric"),
            target_skills=targets,
        )
        for row in questions_row.data
    ]

    suffix = Path(video.filename or "video").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        chunk_size  = 1024 * 1024  # 1 MB
        total_bytes = 0
        while True:
            chunk = video.file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > _MAX_VIDEO_BYTES:
                Path(tmp.name).unlink(missing_ok=True)
                raise HTTPException(413, f"Video exceeds the {_MAX_VIDEO_BYTES // (1024*1024)} MB limit.")
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        report = run_analysis(AnalysisRequest(
            interview_id=    interview_id,
            video_url=       tmp_path,
            questions=       questions,
            scoring_weights= None,
        ))
    except Exception as exc:
        logger.exception("[Analysis] run-upload failed for %s", interview_id)
        raise HTTPException(500, f"Analysis failed: {exc}") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    _persist_report(report, upsert=True)
    return report


@router.get("/{interview_id}", response_model=Report)
def get_analysis(interview_id: str):
    return _load_report(interview_id)
