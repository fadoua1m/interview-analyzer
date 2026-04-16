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

class TextMetrics(BaseModel):
    """Text analysis metrics extracted from TextAnalysisResult."""
    clarity_score:          float      = 0.0   # 0-10
    confidence_level:       str        = "unknown"  # high | medium | low | unknown
    relevance_score:        float      = 0.0   # 0-10
    relevance_per_question: list[float]= Field(default_factory=list)



class DetectedSkill(BaseModel):
    """Soft skill/competency detected in interview answers."""
    name:        str  # e.g. "leadership", "team_orientation"
    strength:    str  # not_demonstrated | weak | moderate | strong
    quote:       str  # verbatim evidence from the answer
    description: str  # reasoning behind the rating


class SoftSkillEvidence(BaseModel):
    """Soft skill evidence block for the HR report view."""
    name:     str
    strength: str
    quote:    str
    reason:   str


# ── Video Analysis Results ─────────────────────────────────────────────────────

class EmotionTimelinePoint(BaseModel):
    """Single point in the emotion timeline.

    ``emotion_scores`` carries all 7 probabilities (0-1 each) per sampled frame,
    enabling the recruiter UI to render a per-emotion time-series chart.
    """
    timestamp_sec:    float
    dominant_emotion: str
    confidence:       float                            # max prob 0-1
    emotion_scores:   dict[str, float] = Field(default_factory=dict)  # all 7 probs 0-1


class EmotionMetrics(BaseModel):
    """Emotion and emotional-stability analysis for the whole interview."""
    dominant_emotion:     str                          = "unknown"
    emotion_distribution: dict[str, float]             = Field(default_factory=dict)  # % per emotion (0-100)
    top_emotions:         dict[str, float]             = Field(default_factory=dict)  # top-3 emotions
    emotion_timeline:     list[EmotionTimelinePoint]   = Field(default_factory=list)
    volatility:           float                        = 0.0   # 0-100 (0=stable, 100=highly volatile)
    positive_ratio:       float                        = 0.0   # % frames showing happy/surprise (0-100)
    confidence:           float                        = 0.0   # avg max-emotion confidence (0-100)


class EngagementMetrics(BaseModel):
    """Behavioral engagement and focus metrics.

    All numeric fields are on a 0-100 scale.
    Note: head_stability maps to emotion-stability; gaze_consistency maps to
    face-detection-rate (ViT-Face-Expression does not provide head-pose or gaze).
    """
    engagement_rate:     float = 0.0   # 0-100  composite score
    head_stability:      float = 0.0   # 0-100  (emotion stability proxy)
    gaze_consistency:    float = 0.0   # 0-100  (face detection rate proxy)
    face_detection_rate: float = 0.0   # 0-100  % frames with face detected
    focus_quality:       str   = "low" # low | medium | high




# ── Unified Report Schema ──────────────────────────────────────────────────────

class Report(BaseModel):
    """Comprehensive candidate interview report."""
    # Metadata
    interview_id:   str
    qa_pairs_count: int
    generated_at:   datetime

    # Text Analysis
    text_metrics:    TextMetrics
    detected_skills: list[DetectedSkill] = Field(default_factory=list)

    # Video Analysis
    emotion_metrics:    EmotionMetrics
    engagement_metrics: EngagementMetrics

    # HR Assessment
    overall_score:    float      = 0.0           # 0-100
    decision:         str        = "REVIEW"      # PROCEED | REVIEW | REJECT
    decision_reasons: list[str]  = Field(default_factory=list)
    hr_summary:       str        = ""

