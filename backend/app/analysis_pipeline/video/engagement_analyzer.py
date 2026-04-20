"""
Engagement Analyzer
===================
Measures candidate engagement from signals that are *actually available*
from the ViT-Face-Expression model (which provides emotion scores and face
detection confidence, but NOT head-pose or gaze direction).

Signal sources:
  1. face_detection_rate   — % of sampled frames where a face was found
                             (proxy for "showing up and staying in frame")
  2. emotion_stability     — inverse of emotion volatility
                             (frequent emotion changes → less composed / focused)
  3. positive_neutral_ratio— % of frames showing positive or neutral emotion
                             (calm, attentive demeanour)
  4. avg_confidence        — average model confidence when a face IS detected
                             (low confidence may indicate occlusion or poor framing)

Composite engagement_rate = weighted combination of the above.

NOT used (no data source): yaw, pitch, gaze direction.
"""

import numpy as np

from app.config import settings


class EngagementMetrics:
    """Engagement analysis result (0-100 scale for all numeric fields)."""

    def __init__(
        self,
        engagement_rate:     float = 0.0,   # 0-100 composite
        face_detection_rate: float = 0.0,   # % frames with face detected
        emotion_stability:   float = 0.0,   # 100 = perfectly stable emotion
        positive_neutral_ratio: float = 0.0,# % frames with positive or neutral emotion
        avg_detection_confidence: float = 0.0, # avg model confidence (0-100)
        focus_quality:       str   = "low", # low / medium / high
    ):
        self.engagement_rate          = round(max(0.0, min(100.0, engagement_rate)), 2)
        self.face_detection_rate      = round(max(0.0, min(100.0, face_detection_rate)), 2)
        self.emotion_stability        = round(max(0.0, min(100.0, emotion_stability)), 2)
        self.positive_neutral_ratio   = round(max(0.0, min(100.0, positive_neutral_ratio)), 2)
        self.avg_detection_confidence = round(max(0.0, min(100.0, avg_detection_confidence)), 2)
        self.focus_quality            = focus_quality if focus_quality in {"low", "medium", "high"} else "low"

        # Legacy compatibility — callers that check gaze_consistency or head_stability
        # receive a sensible fallback rather than AttributeError
        self.gaze_consistency = self.face_detection_rate
        self.head_stability   = self.emotion_stability


# ── Signal helpers ─────────────────────────────────────────────────────────────

def _face_detection_rate(frame_records: list[dict]) -> float:
    if not frame_records:
        return 0.0
    detected = sum(1 for r in frame_records if r.get("face_detected", False))
    return (detected / len(frame_records)) * 100.0


def _emotion_stability(frame_records: list[dict]) -> float:
    """100 minus the fraction of consecutive frame pairs with an emotion change (× 100)."""
    detected = [r for r in frame_records if r.get("face_detected", False)]
    if len(detected) < 2:
        return 100.0

    transitions = sum(
        1
        for prev, curr in zip(detected, detected[1:])
        if prev.get("dominant_emotion") != curr.get("dominant_emotion")
    )
    volatility = (transitions / (len(detected) - 1)) * 100.0
    return max(0.0, 100.0 - volatility)


def _positive_neutral_ratio(frame_records: list[dict]) -> float:
    """% of detected frames showing happy, surprise, or neutral emotion."""
    _POSITIVE = {"happy", "surprise", "neutral"}
    detected = [r for r in frame_records if r.get("face_detected", False)]
    if not detected:
        return 0.0
    pos = sum(1 for r in detected if r.get("dominant_emotion", "neutral") in _POSITIVE)
    return (pos / len(detected)) * 100.0


def _avg_detection_confidence(frame_records: list[dict]) -> float:
    """Average model confidence (0-100) across frames where a face was detected."""
    confs = [
        r["confidence"] * 100.0
        for r in frame_records
        if r.get("face_detected", False) and "confidence" in r
    ]
    return float(np.mean(confs)) if confs else 0.0


def _focus_quality(engagement_rate: float) -> str:
    high_thr = getattr(settings, "engagement_focus_high_threshold",   70.0)
    med_thr  = getattr(settings, "engagement_focus_medium_threshold", 42.0)
    if engagement_rate >= high_thr:
        return "high"
    elif engagement_rate >= med_thr:
        return "medium"
    return "low"


# ── Public API ─────────────────────────────────────────────────────────────────

def analyze_engagement(frame_records: list[dict]) -> EngagementMetrics:
    """Compute engagement metrics from per-frame emotion-detection records.

    Args:
        frame_records: list of dicts with keys:
            face_detected   (bool)
            dominant_emotion(str)
            emotion_scores  (dict[str, float])
            confidence      (float 0-1)

    Returns:
        EngagementMetrics
    """
    fdr  = _face_detection_rate(frame_records)
    stab = _emotion_stability(frame_records)
    pnr  = _positive_neutral_ratio(frame_records)
    adc  = _avg_detection_confidence(frame_records)

    engagement = (
        fdr  * getattr(settings, "engagement_weight_face_detection",    0.40) +
        stab * getattr(settings, "engagement_weight_emotion_stability",  0.30) +
        pnr  * getattr(settings, "engagement_weight_positive_neutral",   0.20) +
        adc  * getattr(settings, "engagement_weight_avg_confidence",     0.10)
    )

    return EngagementMetrics(
        engagement_rate=          engagement,
        face_detection_rate=      fdr,
        emotion_stability=        stab,
        positive_neutral_ratio=   pnr,
        avg_detection_confidence= adc,
        focus_quality=            _focus_quality(engagement),
    )
