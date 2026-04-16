import uuid
from sqlalchemy import Column, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
from app.supabase_client import Base
from app.models.enums import SeniorityLevel

class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title           = Column(String, nullable=False)
    company         = Column(String, nullable=False)
    description     = Column(Text, nullable=False)
    requirements    = Column(Text, nullable=False)
    seniority_level = Column(SAEnum(SeniorityLevel), nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())