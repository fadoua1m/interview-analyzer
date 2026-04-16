from __future__ import annotations

from typing import Any

from app.supabase_client import supabase

SOFTSKILLS_TABLE = "softskills_bank"


def _normalize_key(value: str) -> str:
    return (value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _normalize_language(value: str | None) -> str:
    lang = (value or "en").strip().lower()
    if lang not in {"en", "fr"}:
        return "en"
    return lang


def list_softskills(language: str | None = None, active: bool | None = None) -> list[dict[str, Any]]:
    query = supabase.table(SOFTSKILLS_TABLE).select("*").order("created_at", desc=False)

    if language:
        query = query.eq("language", _normalize_language(language))

    if active is not None:
        query = query.eq("active", bool(active))

    result = query.execute()
    return result.data or []


def get_softskill_keys(active_only: bool = True) -> list[str]:
    query = supabase.table(SOFTSKILLS_TABLE).select("key")
    if active_only:
        query = query.eq("active", True)

    data = query.execute().data or []
    keys = {_normalize_key(row.get("key", "")) for row in data if row.get("key")}
    keys.discard("")
    return sorted(keys)


def get_competency_bank_for_language(language: str | None = None) -> dict[str, str]:
    normalized_language = _normalize_language(language)
    rows = list_softskills(language=normalized_language, active=True)
    if not rows and normalized_language != "en":
        rows = list_softskills(language="en", active=True)

    bank = {
        _normalize_key(row.get("key", "")): row.get("description", "")
        for row in rows
        if row.get("key") and row.get("description")
    }
    return {k: v for k, v in bank.items() if k and v}


def validate_softskill_keys(keys: list[str]) -> tuple[list[str], list[str]]:
    normalized_input = []
    seen = set()
    for key in keys or []:
        normalized = _normalize_key(key)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_input.append(normalized)

    allowed = set(get_softskill_keys(active_only=True))
    valid = [key for key in normalized_input if key in allowed]
    invalid = [key for key in normalized_input if key not in allowed]
    return valid, invalid


def normalize_language(value: str | None) -> str:
    return _normalize_language(value)


def normalize_key(value: str) -> str:
    return _normalize_key(value)
