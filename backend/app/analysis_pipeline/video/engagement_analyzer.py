"""
Engagement Analyzer
===================
Measures candidate engagement from signals available from ViT-Face-Expression
(emotion scores + face detection confidence).  Head-pose and gaze direction
are NOT available — no fabricated values.

Composite engagement_rate = weighted combination of:
  face_detection_rate (0.40) — presence and visibility
  emotion_stability   (0.40) — composed, non-erratic emotional presentation
  detection_quality   (0.20) — avg model confidence (proxy for image quality)
"""

import logging
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class EngagementMetrics:
    """Engagement analysis result (0-100 scale for all numeric fields)."""

    def __init__(
        self,
        engagement_rate:     float = 0.0,
        face_detection_rate: float = 0.0,
        emotion_stability:   float = 0.0,   # 100 = perfectly stable
        detection_quality:   float = 0.0,   # avg model confidence (0-100)
        focus_quality:       str   = "low",
    ):
        self.engagement_rate     = round(max(0.0, min(100.0, engagement_rate)), 2)
        self.face_detection_rate = round(max(0.0, min(100.0, face_detection_rate)), 2)
        self.emotion_stability   = round(max(0.0, min(100.0, emotion_stability)), 2)
        self.detection_quality   = round(max(0.0, min(100.0, detection_quality)), 2)
        self.focus_quality       = focus_quality if focus_quality in {"low", "medium", "high"} else "low"


# ── Signal helpers ─────────────────────────────────────────────────────────────

def _face_detection_rate(frame_records: list[dict]) -> float:
    if not frame_records:
        return 0.0
    detected = sum(1 for r in frame_records if r.get("face_detected", False))
    return (detected / len(frame_records)) * 100.0


def _emotion_stability(frame_records: list[dict]) -> float:
    """100 minus the fraction of consecutive detected-frame pairs with an emotion change (×100)."""
    detected = [r for r in frame_records if r.get("face_detected", False)]
    if len(detected) < 2:
        return 100.0
    transitions = sum(
        1 for prev, curr in zip(detected, detected[1:])
        if prev.get("dominant_emotion") != curr.get("dominant_emotion")
    )
    volatility = (transitions / (len(detected) - 1)) * 100.0
    return max(0.0, 100.0 - volatility)


def _detection_quality(frame_records: list[dict]) -> float:
    """Average model confidence (0-100) when a face is detected."""
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
    """Compute engagement metrics from per-frame emotion-detection records."""
    fdr  = _face_detection_rate(frame_records)
    stab = _emotion_stability(frame_records)
    dq   = _detection_quality(frame_records)

    engagement = (
        fdr  * getattr(settings, "engagement_weight_face_detection",   0.40) +
        stab * getattr(settings, "engagement_weight_emotion_stability", 0.40) +
        dq   * getattr(settings, "engagement_weight_avg_confidence",    0.20)
    )

    return EngagementMetrics(
        engagement_rate=     engagement,
        face_detection_rate= fdr,
        emotion_stability=   stab,
        detection_quality=   dq,
        focus_quality=       _focus_quality(engagement),
    )
