# app/routes/job_description.py
import logging
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.supabase_client import supabase
from app.schemas.job_description import (
    JobDescriptionCreate,
    JobDescriptionUpdate,
    JobDescriptionResponse,
)
from app.schemas.interview import AITextResponse
from app.services import description_ai

router = APIRouter(prefix="/jobs", tags=["Jobs"])
logger = logging.getLogger(__name__)

TABLE = "job_descriptions"


def _sanitize_job_write_payload(data: dict) -> dict:
    """Remove fields not present in the current job_descriptions table."""
    clean = dict(data)
    clean.pop("language", None)
    return clean


# ════════════════════════════════════════════════════════════════════════════
#  CRUD
# ════════════════════════════════════════════════════════════════════════════

@router.get("", response_model=list[JobDescriptionResponse])
def list_jobs():
    result = supabase.table(TABLE).select("*").order("created_at", desc=True).execute()
    return result.data


@router.get("/{id}", response_model=JobDescriptionResponse)
def get_job(id: str):
    result = supabase.table(TABLE).select("*").eq("id", id).execute()
    if not result.data:
        raise HTTPException(404, "Job not found")
    return result.data[0]


@router.post("", response_model=JobDescriptionResponse, status_code=201)
def create_job(payload: JobDescriptionCreate):
    data = _sanitize_job_write_payload(payload.model_dump())
    result = supabase.table(TABLE).insert(data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create job")
    return result.data[0]


@router.patch("/{id}", response_model=JobDescriptionResponse)
def update_job(id: str, payload: JobDescriptionUpdate):
    data = _sanitize_job_write_payload(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(400, "No fields to update")

    existing = supabase.table(TABLE).select("id").eq("id", id).execute()
    if not existing.data:
        raise HTTPException(404, "Job not found")

    result = supabase.table(TABLE).update(data).eq("id", id).execute()
    if not result.data:
        raise HTTPException(500, "Failed to update job")
    return result.data[0]


@router.delete("/{id}", status_code=204)
def delete_job(id: str):
    existing = supabase.table(TABLE).select("id").eq("id", id).execute()
    if not existing.data:
        raise HTTPException(404, "Job not found")
    supabase.table(TABLE).delete().eq("id", id).execute()


# ════════════════════════════════════════════════════════════════════════════
#  AI — description & requirements
# ════════════════════════════════════════════════════════════════════════════

class EnhanceDescriptionRequest(BaseModel):
    title:       str
    company:     str
    description: str
    language:    str = "en"

class GenerateRequirementsRequest(BaseModel):
    title:       str
    company:     str
    description: str
    language:    str = "en"

class EnhanceRequirementsRequest(BaseModel):
    title:        str
    requirements: str
    language:     str = "en"


@router.post("/ai/enhance-description", response_model=AITextResponse)
def enhance_description(payload: EnhanceDescriptionRequest):
    if not payload.description.strip():
        raise HTTPException(400, "Description cannot be empty")
    try:
        return {"result": description_ai.enhance_description(
            payload.title, payload.company, payload.description, payload.language
        )}
    except Exception as e:
        logger.error("enhance_description failed: %s", e)
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")


@router.post("/ai/generate-requirements", response_model=AITextResponse)
def generate_requirements(payload: GenerateRequirementsRequest):
    if not payload.description.strip():
        raise HTTPException(400, "Description is required to generate requirements")
    try:
        return {"result": description_ai.generate_requirements(
            payload.title, payload.company, payload.description, payload.language
        )}
    except Exception as e:
        logger.error("generate_requirements failed: %s", e)
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")


@router.post("/ai/enhance-requirements", response_model=AITextResponse)
def enhance_requirements(payload: EnhanceRequirementsRequest):
    if not payload.requirements.strip():
        raise HTTPException(400, "Requirements cannot be empty")
    try:
        return {"result": description_ai.enhance_requirements(
            payload.title, payload.requirements, payload.language
        )}
    except Exception as e:
        logger.error("enhance_requirements failed: %s", e)
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")
