from app.schemas.job_description import (
    JobDescriptionCreate,
    JobDescriptionUpdate,
    JobDescriptionResponse,
)
from app.schemas.interview import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    InterviewCreate,
    InterviewUpdate,
    InterviewResponse,
    InterviewWithQuestions,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    EnhanceQuestionRequest,
    AITextResponse,
    GenerateRubricRequest,
    EnhanceRubricRequest,
)
from app.schemas.analysis import (
    QuestionInput,
    AnalysisRequest,
    QAPair,
    DetectedSkill,
    TextMetrics,
    EmotionMetrics,
    EmotionTimelinePoint,
    EngagementMetrics,
    Report
)
from app.schemas.softskills import (
    SoftSkillBankCreate,
    SoftSkillBankUpdate,
    SoftSkillBankResponse,
    SoftSkillKeysResponse,
)

__all__ = [
    # Job description
    "JobDescriptionCreate",
    "JobDescriptionUpdate",
    "JobDescriptionResponse",
    # Interview
    "QuestionCreate",
    "QuestionUpdate",
    "QuestionResponse",
    "InterviewCreate",
    "InterviewUpdate",
    "InterviewResponse",
    "InterviewWithQuestions",
    "GenerateQuestionsRequest",
    "GenerateQuestionsResponse",
    "EnhanceQuestionRequest",
    "AITextResponse",
    "GenerateRubricRequest",
    "EnhanceRubricRequest",
    # Analysis
    "QuestionInput",
    "AnalysisRequest",
    "QAPair",
    "DetectedSkill",
    "TextMetrics",
    "EmotionMetrics",
    "EmotionTimelinePoint",
    "EngagementMetrics",
    "Report",
    # Soft skills
    "SoftSkillBankCreate",
    "SoftSkillBankUpdate",
    "SoftSkillBankResponse",
    "SoftSkillKeysResponse",
]
