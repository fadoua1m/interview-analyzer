from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SoftSkillBankCreate(BaseModel):
    key: str
    language: str = "en"
    display_name: str
    description: str
    active: bool = True


class SoftSkillBankUpdate(BaseModel):
    key: Optional[str] = None
    language: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class SoftSkillBankResponse(BaseModel):
    id: str
    key: str
    language: str
    display_name: str
    description: str
    active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SoftSkillKeysResponse(BaseModel):
    keys: list[str] = Field(default_factory=list)
