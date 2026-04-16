from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.schemas.softskills import (
    SoftSkillBankCreate,
    SoftSkillBankUpdate,
    SoftSkillBankResponse,
    SoftSkillKeysResponse,
)
from app.services.softskills_bank import (
    SOFTSKILLS_TABLE,
    list_softskills,
    normalize_key,
    normalize_language,
)
from app.supabase_client import supabase

router = APIRouter(prefix="/softskills", tags=["SoftSkills"])


@router.get("", response_model=list[SoftSkillBankResponse])
def get_softskills_bank(
    language: str | None = Query(default=None),
    active: bool | None = Query(default=None),
):
    try:
        return list_softskills(language=language, active=active)
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch softskills bank: {e}")


@router.get("/keys", response_model=SoftSkillKeysResponse)
def get_softskill_keys(
    language: str | None = Query(default=None),
    active: bool = Query(default=True),
):
    try:
        rows = list_softskills(language=language, active=active)
        keys = sorted({normalize_key(row.get("key", "")) for row in rows if row.get("key")})
        return {"keys": [k for k in keys if k]}
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch softskill keys: {e}")


@router.post("", response_model=SoftSkillBankResponse, status_code=201)
def create_softskill(payload: SoftSkillBankCreate):
    key = normalize_key(payload.key)
    if not key:
        raise HTTPException(400, "Softskill key is required")

    language = normalize_language(payload.language)

    existing = (
        supabase.table(SOFTSKILLS_TABLE)
        .select("id")
        .eq("key", key)
        .eq("language", language)
        .execute()
    )
    if existing.data:
        raise HTTPException(409, "Softskill key already exists for this language")

    data = payload.model_dump()
    data["key"] = key
    data["language"] = language

    try:
        result = supabase.table(SOFTSKILLS_TABLE).insert(data).execute()
        if not result.data:
            raise HTTPException(500, "Failed to create softskill")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to create softskill: {e}")


@router.patch("/{softskill_id}", response_model=SoftSkillBankResponse)
def update_softskill(softskill_id: str, payload: SoftSkillBankUpdate):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(400, "No fields to update")

    if "key" in data and data["key"] is not None:
        data["key"] = normalize_key(data["key"])
    if "language" in data and data["language"] is not None:
        data["language"] = normalize_language(data["language"])

    exists = (
        supabase.table(SOFTSKILLS_TABLE)
        .select("id")
        .eq("id", softskill_id)
        .execute()
    )
    if not exists.data:
        raise HTTPException(404, "Softskill not found")

    data["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        result = supabase.table(SOFTSKILLS_TABLE).update(data).eq("id", softskill_id).execute()
        if not result.data:
            raise HTTPException(500, "Failed to update softskill")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update softskill: {e}")


@router.delete("/{softskill_id}", status_code=204)
def delete_softskill(softskill_id: str):
    exists = (
        supabase.table(SOFTSKILLS_TABLE)
        .select("id")
        .eq("id", softskill_id)
        .execute()
    )
    if not exists.data:
        raise HTTPException(404, "Softskill not found")

    try:
        supabase.table(SOFTSKILLS_TABLE).delete().eq("id", softskill_id).execute()
    except Exception as e:
        raise HTTPException(500, f"Failed to delete softskill: {e}")
