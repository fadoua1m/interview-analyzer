# app/routes/interview.py
import traceback
import shutil
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.supabase_client import supabase
from app.schemas.interview import (
    InterviewCreate,
    InterviewUpdate,
    InterviewResponse,
    InterviewWithQuestions,
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    EnhanceQuestionRequest,
    AITextResponse,
    GenerateRubricRequest,
    EnhanceRubricRequest,
    CandidateAssignCreate,
    CandidateAssignmentResponse,
    CandidateAccessResponse,
    CandidateSubmissionResponse,
)
from app.schemas.analysis import AnalysisRequest, QuestionInput, Report
from app.analysis_pipeline.pipeline import run_analysis
from app.services import interview_ai
from app.services.softskills_bank import validate_softskill_keys

router = APIRouter(prefix="/interviews", tags=["Interviews"])

INTERVIEWS = "interviews"
QUESTIONS  = "interview_questions"
CANDIDATES = "interview_candidates"


def _normalize_question_row(row: dict) -> dict:
    return dict(row)


def _normalize_interview_row(row: dict) -> dict:
    data = dict(row)
    target = data.get("target_softskills")
    data["target_softskills"] = target if isinstance(target, list) else []
    return data


def _normalize_candidate_row(row: dict) -> dict:
    data = dict(row)
    payload = data.get("analysis_payload")
    data["analysis_payload"] = payload if isinstance(payload, dict) else None
    return data


def _build_candidate_analysis_payload(report: Report) -> dict:
    """Serialize the full Report for storage in interview_candidates.analysis_payload."""
    return report.model_dump(mode="json")


def _raise_candidate_table_setup_error(exc: Exception) -> None:
    message = str(exc)
    if "interview_candidates" in message:
        raise HTTPException(
            503,
            "Candidate workflow table is not initialized. Run backend/sql/interview_candidates_setup.sql in Supabase SQL editor, then retry.",
        )


def _validate_softskills_or_400(skills: list[str]) -> list[str]:
    valid, invalid = validate_softskill_keys(skills)
    if invalid:
        raise HTTPException(400, f"Invalid softskill keys: {', '.join(invalid)}")
    return valid


# ════════════════════════════════════════════════════════════════════════════
#  INTERVIEWS CRUD
# ════════════════════════════════════════════════════════════════════════════

@router.post("", response_model=InterviewResponse, status_code=201)
def create_interview(payload: InterviewCreate):
    # one-to-one: one job → one interview
    existing = (
        supabase.table(INTERVIEWS)
        .select("id")
        .eq("job_id", payload.job_id)
        .execute()
    )
    if existing.data:
        raise HTTPException(409, "This job already has an interview.")

    data         = payload.model_dump()
    data["type"] = payload.type.value
    data["target_softskills"] = _validate_softskills_or_400(payload.target_softskills)

    result = supabase.table(INTERVIEWS).insert(data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create interview")
    return _normalize_interview_row(result.data[0])


@router.get("", response_model=list[InterviewResponse])
def list_interviews():
    result = (
        supabase.table(INTERVIEWS)
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return [_normalize_interview_row(row) for row in (result.data or [])]


@router.get("/job/{job_id}", response_model=InterviewResponse | None)
def get_interview_by_job(job_id: str):
    """Return the single interview for a job, or null if none exists."""
    result = (
        supabase.table(INTERVIEWS)
        .select("*")
        .eq("job_id", job_id)
        .execute()
    )
    return _normalize_interview_row(result.data[0]) if result.data else None


@router.get("/{id}", response_model=InterviewWithQuestions)
def get_interview(id: str):
    """Return interview with all its questions ordered by order_index."""
    interview = (
        supabase.table(INTERVIEWS)
        .select("*")
        .eq("id", id)
        .execute()
    )
    if not interview.data:
        raise HTTPException(404, "Interview not found")

    questions = (
        supabase.table(QUESTIONS)
        .select("*")
        .eq("interview_id", id)
        .order("order_index", desc=False)
        .execute()
    )

    data = _normalize_interview_row(interview.data[0])
    data["questions"] = [_normalize_question_row(q) for q in (questions.data or [])]
    return data


@router.patch("/{id}", response_model=InterviewResponse)
def update_interview(id: str, payload: InterviewUpdate):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(400, "No fields to update")

    if "type" in data and data["type"] is not None:
        data["type"] = data["type"].value
    if "target_softskills" in data and data["target_softskills"] is not None:
        data["target_softskills"] = _validate_softskills_or_400(data["target_softskills"])

    existing = supabase.table(INTERVIEWS).select("id").eq("id", id).execute()
    if not existing.data:
        raise HTTPException(404, "Interview not found")

    data["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = supabase.table(INTERVIEWS).update(data).eq("id", id).execute()
    if not result.data:
        raise HTTPException(500, "Failed to update interview")
    return _normalize_interview_row(result.data[0])


@router.delete("/{id}", status_code=204)
def delete_interview(id: str):
    existing = supabase.table(INTERVIEWS).select("id").eq("id", id).execute()
    if not existing.data:
        raise HTTPException(404, "Interview not found")
    supabase.table(INTERVIEWS).delete().eq("id", id).execute()


# ════════════════════════════════════════════════════════════════════════════
#  QUESTIONS CRUD
# ════════════════════════════════════════════════════════════════════════════

@router.post("/{interview_id}/questions", response_model=QuestionResponse, status_code=201)
def create_question(interview_id: str, payload: QuestionCreate):
    existing = (
        supabase.table(INTERVIEWS)
        .select("id")
        .eq("id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Interview not found")

    data                 = payload.model_dump()
    data["interview_id"] = interview_id

    result = supabase.table(QUESTIONS).insert(data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create question")
    return _normalize_question_row(result.data[0])


@router.patch("/{interview_id}/questions/{question_id}", response_model=QuestionResponse)
def update_question(interview_id: str, question_id: str, payload: QuestionUpdate):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(400, "No fields to update")

    existing = (
        supabase.table(QUESTIONS)
        .select("id")
        .eq("id", question_id)
        .eq("interview_id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Question not found")

    result = supabase.table(QUESTIONS).update(data).eq("id", question_id).execute()
    if not result.data:
        raise HTTPException(500, "Failed to update question")
    return _normalize_question_row(result.data[0])


@router.delete("/{interview_id}/questions/{question_id}", status_code=204)
def delete_question(interview_id: str, question_id: str):
    existing = (
        supabase.table(QUESTIONS)
        .select("id")
        .eq("id", question_id)
        .eq("interview_id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Question not found")
    supabase.table(QUESTIONS).delete().eq("id", question_id).execute()


# ════════════════════════════════════════════════════════════════════════════
#  AI — question generation & enhancement (belongs to interview)
# ════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{interview_id}/ai/generate-questions",
    response_model=GenerateQuestionsResponse,
)
def generate_questions(interview_id: str, payload: GenerateQuestionsRequest):
    """
    Generate AI interview questions tailored to:
    - Interview type  (behavioral / technical / hr / mixed)
    - Seniority level (junior / mid / senior / lead)
    - Job description + requirements
    """
    existing = (
        supabase.table(INTERVIEWS)
        .select("id")
        .eq("id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Interview not found")

    if not payload.description.strip() and not payload.requirements.strip():
        raise HTTPException(400, "Provide at least a description or requirements")

    try:
        questions = interview_ai.generate_questions(
            title=           payload.title,
            company=         payload.company,
            interview_type=  payload.interview_type,
            seniority_level= payload.seniority_level,
            description=     payload.description,
            requirements=    payload.requirements,
            count=           payload.count,
        )
        return {"questions": questions}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")


@router.post(
    "/{interview_id}/questions/{question_id}/ai/enhance",
    response_model=AITextResponse,
)
def enhance_question(interview_id: str, question_id: str, payload: EnhanceQuestionRequest):
    """Rewrite a single question to be sharper, respecting type and seniority."""
    existing = (
        supabase.table(QUESTIONS)
        .select("id")
        .eq("id", question_id)
        .eq("interview_id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Question not found")

    if not payload.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    try:
        return {"result": interview_ai.enhance_question(
            title=           payload.title,
            interview_type=  payload.interview_type,
            seniority_level= payload.seniority_level,
            question=        payload.question,
        )}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")
    
@router.post(
    "/{interview_id}/questions/{question_id}/ai/generate-rubric",
    response_model=AITextResponse,
)
def generate_rubric(interview_id: str, question_id: str, payload: GenerateRubricRequest):
    """Generate a 4-band scoring rubric for a question."""
    existing = (
        supabase.table(QUESTIONS)
        .select("id")
        .eq("id", question_id)
        .eq("interview_id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Question not found")

    if not payload.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    try:
        return {"result": interview_ai.generate_rubric(
            question=        payload.question,
            interview_type=  payload.interview_type,
            seniority_level= payload.seniority_level,
            title=           payload.title,
        )}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")


@router.post(
    "/{interview_id}/questions/{question_id}/ai/enhance-rubric",
    response_model=AITextResponse,
)
def enhance_rubric(interview_id: str, question_id: str, payload: EnhanceRubricRequest):
    """Improve an existing rubric for a question."""
    existing = (
        supabase.table(QUESTIONS)
        .select("id")
        .eq("id", question_id)
        .eq("interview_id", interview_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Question not found")

    if not payload.rubric.strip():
        raise HTTPException(400, "Rubric cannot be empty")

    try:
        return {"result": interview_ai.enhance_rubric(
            question=        payload.question,
            rubric=          payload.rubric,
            interview_type=  payload.interview_type,
            seniority_level= payload.seniority_level,
            title=           payload.title,
        )}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")


@router.post("/{interview_id}/candidates", response_model=CandidateAssignmentResponse, status_code=201)
def assign_candidate(interview_id: str, payload: CandidateAssignCreate):
    interview = (
        supabase.table(INTERVIEWS)
        .select("id")
        .eq("id", interview_id)
        .execute()
    )
    if not interview.data:
        raise HTTPException(404, "Interview not found")

    name = payload.name.strip()
    email = payload.email.strip().lower()
    if not name:
        raise HTTPException(400, "Candidate name is required")
    if not email or "@" not in email:
        raise HTTPException(400, "Valid candidate email is required")

    try:
        exists = (
            supabase.table(CANDIDATES)
            .select("id")
            .eq("interview_id", interview_id)
            .eq("email", email)
            .execute()
        )
    except Exception as exc:
        _raise_candidate_table_setup_error(exc)
        raise
    if exists.data:
        raise HTTPException(409, "Candidate already assigned to this interview")

    row = {
        "interview_id": interview_id,
        "name": name,
        "email": email,
        "status": "assigned",
        "access_token": uuid.uuid4().hex,
    }
    try:
        result = supabase.table(CANDIDATES).insert(row).execute()
    except Exception as exc:
        _raise_candidate_table_setup_error(exc)
        raise
    if not result.data:
        raise HTTPException(500, "Failed to assign candidate")
    return _normalize_candidate_row(result.data[0])


@router.get("/{interview_id}/candidates", response_model=list[CandidateAssignmentResponse])
def list_assigned_candidates(interview_id: str):
    try:
        rows = (
            supabase.table(CANDIDATES)
            .select("*")
            .eq("interview_id", interview_id)
            .order("created_at", desc=False)
            .execute()
        )
    except Exception as exc:
        _raise_candidate_table_setup_error(exc)
        raise
    return [_normalize_candidate_row(row) for row in (rows.data or [])]


@router.get("/candidate-access/{access_token}", response_model=CandidateAccessResponse)
def get_candidate_access(access_token: str):
    try:
        assignment = (
            supabase.table(CANDIDATES)
            .select("*")
            .eq("access_token", access_token)
            .execute()
        )
    except Exception as exc:
        _raise_candidate_table_setup_error(exc)
        raise
    if not assignment.data:
        raise HTTPException(404, "Invalid candidate access link")

    candidate = assignment.data[0]
    interview_id = candidate["interview_id"]

    interview = (
        supabase.table(INTERVIEWS)
        .select("id, title")
        .eq("id", interview_id)
        .execute()
    )
    if not interview.data:
        raise HTTPException(404, "Interview not found")

    questions = (
        supabase.table(QUESTIONS)
        .select("id, question, order_index")
        .eq("interview_id", interview_id)
        .order("order_index", desc=False)
        .execute()
    )

    return {
        "assignment_id": candidate["id"],
        "interview_id": interview_id,
        "interview_title": interview.data[0]["title"],
        "candidate_name": candidate.get("name", "Candidate"),
        "status": candidate.get("status", "assigned"),
        "questions": questions.data or [],
    }


@router.post("/candidate-access/{access_token}/submit", response_model=CandidateSubmissionResponse)
def submit_candidate_video(access_token: str, video: UploadFile = File(...)):
    try:
        assignment = (
            supabase.table(CANDIDATES)
            .select("*")
            .eq("access_token", access_token)
            .execute()
        )
    except Exception as exc:
        _raise_candidate_table_setup_error(exc)
        raise
    if not assignment.data:
        raise HTTPException(404, "Invalid candidate access link")

    candidate = assignment.data[0]
    interview_id = candidate["interview_id"]

    interview_row = (
        supabase.table(INTERVIEWS)
        .select("id, target_softskills")
        .eq("id", interview_id)
        .execute()
    )
    if not interview_row.data:
        raise HTTPException(404, "Interview not found")

    interview_targets = interview_row.data[0].get("target_softskills") or []

    questions_row = (
        supabase.table(QUESTIONS)
        .select("id, question, rubric")
        .eq("interview_id", interview_id)
        .order("order_index", desc=False)
        .execute()
    )
    if not questions_row.data:
        raise HTTPException(400, "This interview has no questions yet.")

    questions = [
        QuestionInput(
            id=row["id"],
            text=row["question"],
            rubric=row.get("rubric"),
            target_skills=interview_targets,
        )
        for row in questions_row.data
    ]

    suffix = Path(video.filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(video.file, tmp)
        tmp_path = tmp.name

    try:
        supabase.table(CANDIDATES).update({
            "status": "submitted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", candidate["id"]).execute()

        report = run_analysis(AnalysisRequest(
            interview_id=interview_id,
            video_url=tmp_path,
            questions=questions,
            scoring_weights=None,
        ))

        analysis_payload = _build_candidate_analysis_payload(report)

        updated = supabase.table(CANDIDATES).update({
            "status": "processed",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "analysis_payload": analysis_payload,
        }).eq("id", candidate["id"]).execute()
        updated_row = _normalize_candidate_row(updated.data[0]) if updated.data else _normalize_candidate_row(candidate)

        return {
            "assignment_id": updated_row["id"],
            "status": updated_row.get("status", "processed"),
            "analysis": updated_row.get("analysis_payload") or analysis_payload,
        }

    except Exception as e:
        traceback.print_exc()
        supabase.table(CANDIDATES).update({
            "status": "failed",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", candidate["id"]).execute()
        raise HTTPException(500, f"Candidate submission analysis failed: {str(e)}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("/{interview_id}/candidates/{candidate_id}/report", response_model=Report)
def get_candidate_report(interview_id: str, candidate_id: str):
    try:
        row = (
            supabase.table(CANDIDATES)
            .select("id, interview_id, analysis_payload")
            .eq("id", candidate_id)
            .eq("interview_id", interview_id)
            .execute()
        )
    except Exception as exc:
        _raise_candidate_table_setup_error(exc)
        raise
    if not row.data:
        raise HTTPException(404, "Candidate assignment not found")

    payload = row.data[0].get("analysis_payload") or {}
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(404, "Candidate report not ready yet")

    try:
        return Report.model_validate(payload)
    except Exception:
        raise HTTPException(500, "Stored report is malformed — resubmit the candidate video")


