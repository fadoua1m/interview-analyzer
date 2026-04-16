import traceback
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import json

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.supabase_client import supabase
from app.schemas.analysis import (
    AnalysisRequest, 
    QuestionInput, 
    Report, 
    TextMetrics,
    EmotionMetrics,
    EmotionTimelinePoint,
    EngagementMetrics,

    DetectedSkill,
)
from app.analysis_pipeline.pipeline import run_analysis

router = APIRouter(prefix="/analysis", tags=["Analysis"])


def _normalize_report_payload(payload: dict, interview_id: str) -> Report:
    """
    Reconstruct Report object from database dictionary.
    
    Converts database-stored data back into properly typed Report schema.
    """
    data = payload or {}
    
    # Extract metadata
    generated_at = data.get("generated_at")
    if isinstance(generated_at, str):
        generated_at = datetime.fromisoformat(generated_at)
    else:
        generated_at = datetime.now(timezone.utc) if not generated_at else generated_at
    
    # Extract decision reasons
    reasons = data.get("decision_reasons", [])
    if not isinstance(reasons, list):
        reasons = [str(reasons)] if str(reasons or "").strip() else []
    
    
    # Extract text metrics (may be stored as nested dict)
    text_metrics_data = data.get("text_metrics") or {}
    if isinstance(text_metrics_data, str):
        try:
            text_metrics_data = json.loads(text_metrics_data)
        except:
            text_metrics_data = {}
    
    text_metrics = TextMetrics(
        clarity_score=float(text_metrics_data.get("clarity_score", 0)),
        confidence_level=text_metrics_data.get("confidence_level", "medium"),
        relevance_score=float(text_metrics_data.get("relevance_score", 0)),
        relevance_per_question=text_metrics_data.get("relevance_per_question", []),

    )
    
    # Extract emotion metrics
    emotion_metrics_data = data.get("emotion_metrics") or {}
    if isinstance(emotion_metrics_data, str):
        try:
            emotion_metrics_data = json.loads(emotion_metrics_data)
        except:
            emotion_metrics_data = {}
    
    emotion_timeline = []
    for point_data in emotion_metrics_data.get("emotion_timeline", []):
        emotion_timeline.append(EmotionTimelinePoint(
            timestamp_sec=    float(point_data.get("timestamp_sec", 0)),
            dominant_emotion= point_data.get("dominant_emotion", "neutral"),
            confidence=       float(point_data.get("confidence", 0.5)),
            emotion_scores=   {
                k: float(v)
                for k, v in (point_data.get("emotion_scores") or {}).items()
            },
        ))
    
    emotion_metrics = EmotionMetrics(
        dominant_emotion=emotion_metrics_data.get("dominant_emotion", "neutral"),
        emotion_distribution=emotion_metrics_data.get("emotion_distribution", {}),
        top_emotions=emotion_metrics_data.get("top_emotions", {}),
        emotion_timeline=emotion_timeline,
        volatility=float(emotion_metrics_data.get("volatility", 50)),
        positive_ratio=float(emotion_metrics_data.get("positive_ratio", 0.5)),
        confidence=float(emotion_metrics_data.get("confidence", 0.5)),
    )
    
    # Extract engagement metrics
    engagement_metrics_data = data.get("engagement_metrics") or {}
    if isinstance(engagement_metrics_data, str):
        try:
            engagement_metrics_data = json.loads(engagement_metrics_data)
        except:
            engagement_metrics_data = {}
    
    engagement_metrics = EngagementMetrics(
        engagement_rate=float(engagement_metrics_data.get("engagement_rate", 0)),
        head_stability=float(engagement_metrics_data.get("head_stability", 0)),
        gaze_consistency=float(engagement_metrics_data.get("gaze_consistency", 0)),
        face_detection_rate=float(engagement_metrics_data.get("face_detection_rate", 0)),
        focus_quality=engagement_metrics_data.get("focus_quality", "low"),
    )
    
    # detected_skills is embedded inside text_metrics jsonb
    # (legacy rows that stored it as a top-level key are also supported)
    raw_skills = (
        text_metrics_data.get("detected_skills")
        or data.get("detected_skills")
        or []
    )
    detected_skills = [
        DetectedSkill(
            name=       s.get("name", ""),
            strength=   s.get("strength", "moderate"),
            quote=      s.get("quote", ""),
            description=s.get("description", ""),
        )
        for s in raw_skills
        if isinstance(s, dict)
    ]
    
    # Construct and return Report
    return Report(
        interview_id=data.get("interview_id") or interview_id,
        qa_pairs_count=int(data.get("qa_pairs_count", 0) or 0),
        generated_at=generated_at,
        text_metrics=text_metrics,
        detected_skills=detected_skills,
        emotion_metrics=emotion_metrics,
        engagement_metrics=engagement_metrics,
        overall_score=float(data.get("overall_score", 0.0) or 0.0),
        decision=data.get("decision", "REVIEW"),
        decision_reasons=reasons,
        hr_summary=data.get("hr_summary", ""),
    )


def _persist_report(report: Report, upsert: bool = False) -> None:
    """
    Persist Report to database.
    
    Saves all fields from Report schema, handling nested objects by converting to dicts/JSON.
    """
    # text_metrics is a jsonb column — embed detected_skills inside it so we
    # don't need a separate column that may not exist in all deployments.
    text_metrics_data = report.text_metrics.model_dump()
    text_metrics_data["detected_skills"] = [
        skill.model_dump() for skill in (report.detected_skills or [])
    ]

    payload = {
        "interview_id":   report.interview_id,
        "qa_pairs_count": report.qa_pairs_count,
        "generated_at":   report.generated_at.isoformat(),

        # text_metrics jsonb carries both TextMetrics fields AND detected_skills
        "text_metrics":      text_metrics_data,

        # Video metrics
        "emotion_metrics":   report.emotion_metrics.model_dump(),
        "engagement_metrics":report.engagement_metrics.model_dump(),

        # HR assessment
        "overall_score":     report.overall_score,
        "decision":          report.decision,
        "decision_reasons":  report.decision_reasons,
        "hr_summary":        report.hr_summary,

    }
    
    try:
        if upsert:
            supabase.table("analysis_results").upsert(
                payload, on_conflict="interview_id"
            ).execute()
        else:
            supabase.table("analysis_results").insert(payload).execute()
        print(f"[DB] Stored analysis for interview_id={report.interview_id}")
    except Exception as e:
        print(f"[DB] FAILED to store analysis for {report.interview_id}: {e}")
        traceback.print_exc()


def _get_interview_targets(interview_id: str) -> list[str]:
    row = (
        supabase.table("interviews")
        .select("target_softskills")
        .eq("id", interview_id)
        .execute()
    )
    return row.data[0].get("target_softskills") or [] if row.data else []


@router.post("/run", response_model=Report)
def run_analysis_route(payload: AnalysisRequest):
    existing = (
        supabase.table("interviews")
        .select("id")
        .eq("id", payload.interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Interview not found")

    targets   = _get_interview_targets(payload.interview_id)
    questions = [
        QuestionInput(
            id=           q.id,
            text=         q.text,
            rubric=       q.rubric,
            target_skills=targets,
        )
        for q in payload.questions
    ]

    try:
        report = run_analysis(AnalysisRequest(
            interview_id=    payload.interview_id,
            video_url=       payload.video_url,
            questions=       questions,
            scoring_weights= payload.scoring_weights,
        ))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Analysis failed: {str(e)}")

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

    targets       = _get_interview_targets(interview_id)
    questions_row = (
        supabase.table("interview_questions")
        .select("id, question, rubric")
        .eq("interview_id", interview_id)
        .order("order_index", desc=False)
        .execute()
    )
    if not questions_row.data:
        raise HTTPException(400, "This interview has no questions.")

    questions = [
        QuestionInput(
            id=           row["id"],
            text=         row["question"],
            rubric=       row.get("rubric"),
            target_skills=targets,
        )
        for row in questions_row.data
    ]

    suffix = Path(video.filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(video.file, tmp)
        tmp_path = tmp.name

    try:
        report = run_analysis(AnalysisRequest(
            interview_id=    interview_id,
            video_url=       tmp_path,
            questions=       questions,
            scoring_weights= None,
        ))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Analysis failed: {str(e)}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    _persist_report(report, upsert=True)
    return report


@router.get("/{interview_id}", response_model=Report)
def get_analysis(interview_id: str):
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
    return _normalize_report_payload(row.data[0], interview_id)



