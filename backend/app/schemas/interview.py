from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.enums import InterviewType

# ── Question schemas ──────────────────────────────────────────────────────────

class QuestionCreate(BaseModel):
    question:    str
    order_index: int = 0
    rubric:      Optional[str] = None

class QuestionUpdate(BaseModel):
    question:    Optional[str] = None
    order_index: Optional[int] = None
    rubric:      Optional[str] = None

class QuestionResponse(BaseModel):
    id:           str
    interview_id: str
    question:     str
    order_index:  int
    rubric:       Optional[str] = None
    created_at:   datetime

    class Config:
        from_attributes = True

# ── Interview schemas ─────────────────────────────────────────────────────────

class InterviewCreate(BaseModel):
    job_id: str
    type:   InterviewType
    title:  str
    notes:  Optional[str] = None
    target_softskills: List[str] = Field(default_factory=list)

class InterviewUpdate(BaseModel):
    type:  Optional[InterviewType] = None
    title: Optional[str]           = None
    notes: Optional[str]           = None
    target_softskills: Optional[List[str]] = None

class InterviewResponse(BaseModel):
    id:         str
    job_id:     str
    type:       InterviewType
    title:      str
    notes:      Optional[str]      = None
    target_softskills: List[str]   = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InterviewWithQuestions(InterviewResponse):
    questions: List[QuestionResponse] = []

# ── AI schemas ────────────────────────────────────────────────────────────────

class GenerateQuestionsRequest(BaseModel):
    title:           str
    company:         str
    interview_type:  str
    seniority_level: str
    description:     str
    requirements:    str
    count:           int = Field(default=10, ge=1, le=20)

class GenerateQuestionsResponse(BaseModel):
    questions: List[str]

class EnhanceQuestionRequest(BaseModel):
    title:           str
    interview_type:  str
    seniority_level: str
    question:        str

class AITextResponse(BaseModel):
    result: str

class GenerateRubricRequest(BaseModel):
    question:        str
    interview_type:  str
    seniority_level: str
    title:           str

class EnhanceRubricRequest(BaseModel):
    question:        str
    rubric:          str
    interview_type:  str
    seniority_level: str
    title:           str


class CandidateAssignCreate(BaseModel):
    name: str
    email: str


class CandidateAssignmentResponse(BaseModel):
    id: str
    interview_id: str
    name: str
    email: str
    status: str
    access_token: str
    submitted_at: Optional[datetime] = None
    created_at: datetime
    analysis_payload: Optional[dict] = None

    class Config:
        from_attributes = True


class CandidateAccessQuestion(BaseModel):
    id: str
    question: str
    order_index: int


class CandidateAccessResponse(BaseModel):
    assignment_id: str
    interview_id: str
    interview_title: str
    candidate_name: str
    status: str
    questions: List[CandidateAccessQuestion] = Field(default_factory=list)


class CandidateSubmissionResponse(BaseModel):
    assignment_id: str
    status: str
    analysis: dict