from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JobDescriptionCreate(BaseModel):
    title:           str
    company:         str
    description:     str
    requirements:    str
    seniority_level: str

    def validate_level(self):
        allowed = {"junior", "mid", "senior", "lead"}
        if self.seniority_level not in allowed:
            raise ValueError(f"seniority_level must be one of {allowed}")

class JobDescriptionUpdate(BaseModel):
    title:           Optional[str] = None
    company:         Optional[str] = None
    description:     Optional[str] = None
    requirements:    Optional[str] = None
    seniority_level: Optional[str] = None

class JobDescriptionResponse(BaseModel):
    id:              str
    title:           str
    company:         str
    description:     str
    requirements:    str
    seniority_level: str
    created_at:      datetime
    updated_at:      Optional[datetime] = None