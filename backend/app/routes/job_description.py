# app/routes/job_description.py
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

TABLE = "job_descriptions"


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
    data = payload.model_dump()
    # seniority_level is a plain str — no .value needed
    result = supabase.table(TABLE).insert(data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create job")
    return result.data[0]


@router.patch("/{id}", response_model=JobDescriptionResponse)
def update_job(id: str, payload: JobDescriptionUpdate):
    data = payload.model_dump(exclude_unset=True)
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

class GenerateRequirementsRequest(BaseModel):
    title:       str
    company:     str
    description: str

class EnhanceRequirementsRequest(BaseModel):
    title:        str
    requirements: str


@router.post("/ai/enhance-description", response_model=AITextResponse)
def enhance_description(payload: EnhanceDescriptionRequest):
    if not payload.description.strip():
        raise HTTPException(400, "Description cannot be empty")
    try:
        return {"result": description_ai.enhance_description(
            payload.title, payload.company, payload.description
        )}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")


@router.post("/ai/generate-requirements", response_model=AITextResponse)
def generate_requirements(payload: GenerateRequirementsRequest):
    if not payload.description.strip():
        raise HTTPException(400, "Description is required to generate requirements")
    try:
        return {"result": description_ai.generate_requirements(
            payload.title, payload.company, payload.description
        )}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")


@router.post("/ai/enhance-requirements", response_model=AITextResponse)
def enhance_requirements(payload: EnhanceRequirementsRequest):
    if not payload.requirements.strip():
        raise HTTPException(400, "Requirements cannot be empty")
    try:
        return {"result": description_ai.enhance_requirements(
            payload.title, payload.requirements
        )}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"AI error: {str(e)}")