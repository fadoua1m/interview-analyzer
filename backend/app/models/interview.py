# app/models/interview.py
import uuid
from sqlalchemy import ARRAY, Column, String, Text, DateTime, Integer, ForeignKey, Enum as SAEnum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.supabase_client import Base
from app.models.enums import InterviewType


class Interview(Base):
    __tablename__ = "interviews"
    __table_args__ = (
        # Enforce one-to-one: one job → one interview
        UniqueConstraint("job_id", name="interviews_job_id_unique"),
    )

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id     = Column(String, ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False, unique=True)
    type       = Column(SAEnum(InterviewType), nullable=False)
    title      = Column(String, nullable=False)
    notes      = Column(Text, nullable=True)
    target_softskills = Column(ARRAY(String), nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    questions  = relationship(
        "InterviewQuestion",
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewQuestion.order_index",
    )


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    interview_id = Column(String, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    question     = Column(Text, nullable=False)
    order_index  = Column(Integer, nullable=False, default=0)
    rubric       = Column(Text, nullable=True)                         
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    interview = relationship("Interview", back_populates="questions")