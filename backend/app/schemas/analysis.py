from pydantic import BaseModel, Field
from datetime import datetime


# ── Request Schemas ────────────────────────────────────────────────────────────

class QuestionInput(BaseModel):
    """Question definition for interview analysis."""
    id:            str
    text:          str
    rubric:        str | None = None
    target_skills: list[str]  = Field(default_factory=list)


class AnalysisRequest(BaseModel):
    """Request to run full interview analysis pipeline."""
    interview_id:    str
    video_url:       str
    questions:       list[QuestionInput]
    scoring_weights: dict[str, float] | None = None
    language:        str                      = "en"


# ── Interview Data Schemas ─────────────────────────────────────────────────────

class QAPair(BaseModel):
    """Question-Answer pair extracted from interview."""
    question:      str
    answer:        str
    rubric:        str | None   = None
    target_skills: list[str]    = Field(default_factory=list)
    start_sec:     float | None = None
    end_sec:       float | None = None


# ── Text Analysis Results ──────────────────────────────────────────────────────

class QuestionDetail(BaseModel):
    """Per-question text analysis breakdown surfaced in the HR report."""
    question:            str          = ""
    relevance_score:     float        = 0.0   # 0-10
    directness_score:    float | None = None  # 0-10 (standard mode only)
    depth_score:         float | None = None  # 0-10 (standard mode only)
    rubric_fit_score:    float | None = None  # 0-10 (rubric mode only)
    clarity_score:       float        = 0.0   # 0-10
    confidence_level:    str          = "unknown"  # high | medium | low
    star_coverage:       str          = "missing"  # full | partial | missing
    brief_justification: str          = ""
    reasoning:           str          = ""
    word_count:          int          = 0


class TextMetrics(BaseModel):
    """Text analysis metrics extracted from TextAnalysisResult."""
    clarity_score:          float                = 0.0
    confidence_level:       str                  = "unknown"
    relevance_score:        float                = 0.0
    relevance_per_question: list[float]          = Field(default_factory=list)
    per_question:           list[QuestionDetail] = Field(default_factory=list)


class DetectedSkill(BaseModel):
    """Soft skill/competency detected in interview answers."""
    name:         str  # e.g. "leadership"
    display_name: str  = ""  # localized label from the bank
    strength:     str  # not_demonstrated | weak | moderate | strong
    quote:        str  # verbatim evidence from the answer
    description:  str  # reasoning behind the rating


class SoftSkillEvidence(BaseModel):
    """Soft skill evidence block for the HR report view."""
    name:     str
    strength: str
    quote:    str
    reason:   str


# ── Video Analysis Results ─────────────────────────────────────────────────────

class EmotionTimelinePoint(BaseModel):
    """Single point in the emotion timeline."""
    timestamp_sec:    float
    dominant_emotion: str
    confidence:       float
    emotion_scores:   dict[str, float] = Field(default_factory=dict)


class EmotionMetrics(BaseModel):
    """Emotion and emotional-stability analysis for the whole interview."""
    dominant_emotion:     str                        = "unknown"
    emotion_distribution: dict[str, float]           = Field(default_factory=dict)
    top_emotions:         dict[str, float]           = Field(default_factory=dict)
    emotion_timeline:     list[EmotionTimelinePoint] = Field(default_factory=list)
    positive_ratio:       float                      = 0.0  # % happy+surprise frames
    neutral_ratio:        float                      = 0.0  # % neutral frames
    negative_ratio:       float                      = 0.0  # % angry+sad+fear+disgust frames
    smile_rate:           float                      = 0.0  # same as positive_ratio
    stress_peak_count:    int                        = 0    # sustained negative bursts (≥3 frames)
    true_volatility:      float                      = 0.0  # L2-distance based volatility (0-100)
    confidence:           float                      = 0.0  # avg detection confidence (0-100)


class EngagementMetrics(BaseModel):
    """Behavioral engagement and focus metrics. All numeric fields 0-100."""
    engagement_rate:     float = 0.0
    emotion_stability:   float = 0.0  # 100 = perfectly stable
    detection_quality:   float = 0.0  # avg model confidence when face detected
    face_detection_rate: float = 0.0  # % frames with face
    focus_quality:       str   = "low"


# ── Unified Report Schema ──────────────────────────────────────────────────────

class Report(BaseModel):
    """Comprehensive candidate interview report."""
    interview_id:   str
    qa_pairs_count: int
    generated_at:   datetime

    text_metrics:    TextMetrics
    detected_skills: list[DetectedSkill] = Field(default_factory=list)

    emotion_metrics:    EmotionMetrics
    engagement_metrics: EngagementMetrics

    overall_score:    float     = 0.0
    decision:         str       = "REVIEW"
    decision_reasons: list[str] = Field(default_factory=list)
    hr_summary:       str       = ""
