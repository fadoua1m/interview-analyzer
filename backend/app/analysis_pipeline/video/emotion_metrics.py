"""
Emotion Metrics
===============
Aggregates EmotionDetectionResult objects into interview-level emotion metrics.

Volatility (L2-based, corrected)
  = average L2 distance between consecutive frame emotion-score vectors,
    normalised to 0-100 (max possible L2 for a 7-dim unit vector ≈ √2 ≈ 1.414).
  This is physically meaningful: it measures how much the full probability
  distribution shifts between frames, not just whether the top label flips.

Stress peaks
  = number of runs of ≥ 3 consecutive frames with a negative dominant emotion
    (angry, sad, fearful, disgusted).  One sustained burst = one peak.
"""

import logging
import numpy as np
from collections import Counter

logger = logging.getLogger(__name__)

_NEGATIVE_EMOTIONS = {"angry", "sad", "fearful", "fear", "disgusted", "disgust"}
_POSITIVE_EMOTIONS = {"happy", "surprise", "surprised"}
_MAX_L2 = float(np.sqrt(2))  # max L2 distance between two probability simplex vectors


# ── EmotionMetrics class ────────────────────────────────────────────────────────

class EmotionMetrics:
    """Comprehensive interview-level emotion analysis metrics."""

    def __init__(
        self,
        emotion_distribution:  dict[str, float],
        dominant_emotion:      str   = "neutral",
        dominant_emotion_pct:  float = 0.0,
        emotion_timeline:      list[dict] | None = None,
        emotion_transitions:   int   = 0,
        transition_rate:       float = 0.0,
        true_volatility:       float = 0.0,   # L2-based (0-100)
        emotion_confidence:    float = 0.0,   # avg detection confidence (0-100)
        positive_ratio:        float = 0.0,   # % happy+surprise frames
        neutral_ratio:         float = 0.0,   # % neutral frames
        negative_ratio:        float = 0.0,   # % angry+sad+fear+disgust frames
        smile_rate:            float = 0.0,   # same as positive_ratio
        stress_peak_count:     int   = 0,     # sustained negative bursts
    ):
        self.emotion_distribution = emotion_distribution
        self.dominant_emotion     = dominant_emotion
        self.dominant_emotion_pct = round(max(0.0, min(100.0, dominant_emotion_pct)), 2)
        self.emotion_timeline     = emotion_timeline or []
        self.emotion_transitions  = emotion_transitions
        self.transition_rate      = round(transition_rate, 2)
        self.emotion_confidence   = round(max(0.0, min(100.0, emotion_confidence)), 2)
        self.true_volatility      = round(max(0.0, min(100.0, true_volatility)), 2)
        self.positive_ratio       = round(max(0.0, min(100.0, positive_ratio)), 2)
        self.neutral_ratio        = round(max(0.0, min(100.0, neutral_ratio)), 2)
        self.negative_ratio       = round(max(0.0, min(100.0, negative_ratio)), 2)
        self.smile_rate           = round(max(0.0, min(100.0, smile_rate)), 2)
        self.stress_peak_count    = max(0, int(stress_peak_count))


# ── Internal helpers ────────────────────────────────────────────────────────────

def _build_timeline(emotion_results: list, video_fps: float) -> list[dict]:
    timeline: list[dict] = []
    for result in emotion_results:
        if hasattr(result, "emotion_scores"):
            frame_idx = getattr(result, "frame_index", len(timeline))
            ts        = round(frame_idx / max(video_fps, 1.0), 3)
            timeline.append({
                "timestamp_sec":    ts,
                "dominant_emotion": result.dominant_emotion,
                "confidence":       result.confidence,
                "emotion_scores":   result.emotion_scores,
                "face_detected":    result.face_detected,
            })
        elif isinstance(result, dict):
            emotions = result.get("emotion", {})
            dominant = max(emotions, key=emotions.get) if emotions else "neutral"
            timeline.append({
                "timestamp_sec":    result.get("timestamp_sec", len(timeline) / max(video_fps, 1.0)),
                "dominant_emotion": dominant,
                "confidence":       max(emotions.values()) if emotions else 0.0,
                "emotion_scores":   emotions,
                "face_detected":    result.get("face_detected", True),
            })
    return timeline


def _get_dominant_emotion(timeline: list[dict]) -> tuple[str, float]:
    detected = [p["dominant_emotion"] for p in timeline if p.get("face_detected")]
    if not detected:
        return "neutral", 0.0
    counter  = Counter(detected)
    dominant, count = counter.most_common(1)[0]
    return dominant, round((count / len(detected)) * 100.0, 2)


def _calculate_emotion_distribution(timeline: list[dict]) -> dict[str, float]:
    detected = [p for p in timeline if p.get("face_detected")]
    if not detected:
        return {}
    counts: dict[str, int] = {}
    for p in detected:
        e = p["dominant_emotion"]
        counts[e] = counts.get(e, 0) + 1
    total = len(detected)
    return {e: round((c / total) * 100.0, 2) for e, c in counts.items()}


def _calculate_transitions(timeline: list[dict]) -> tuple[int, float]:
    detected = [p for p in timeline if p.get("face_detected")]
    if len(detected) < 2:
        return 0, 0.0
    transitions = sum(
        1 for prev, curr in zip(detected, detected[1:])
        if prev["dominant_emotion"] != curr["dominant_emotion"]
    )
    try:
        span_sec = detected[-1]["timestamp_sec"] - detected[0]["timestamp_sec"]
        rate     = (transitions / (span_sec / 60.0)) if span_sec > 0 else 0.0
    except (KeyError, ZeroDivisionError):
        rate = 0.0
    return transitions, round(rate, 2)


def _calculate_true_volatility(timeline: list[dict]) -> float:
    """L2-distance between consecutive frame emotion-score vectors, normalised to 0-100.

    Measures how much the full probability distribution shifts between frames —
    physically more meaningful than counting label flips.
    Max L2 for two probability vectors ≈ √2, so we normalise by that.
    """
    detected = [p for p in timeline if p.get("face_detected") and p.get("emotion_scores")]
    if len(detected) < 2:
        return 0.0

    emotions = sorted(set(k for p in detected for k in p["emotion_scores"]))
    if not emotions:
        return 0.0

    l2_distances: list[float] = []
    for prev, curr in zip(detected, detected[1:]):
        v1 = np.array([prev["emotion_scores"].get(e, 0.0) for e in emotions], dtype=float)
        v2 = np.array([curr["emotion_scores"].get(e, 0.0) for e in emotions], dtype=float)
        l2_distances.append(float(np.linalg.norm(v1 - v2)))

    avg_l2 = float(np.mean(l2_distances)) if l2_distances else 0.0
    return round(min((avg_l2 / _MAX_L2) * 100.0, 100.0), 2)


def _calculate_avg_confidence(timeline: list[dict]) -> float:
    confs = [p["confidence"] for p in timeline if p.get("face_detected") and "confidence" in p]
    return float(np.mean(confs)) if confs else 0.0


def _calculate_ratios(distribution: dict[str, float]) -> tuple[float, float, float, float]:
    """Returns (positive_ratio, neutral_ratio, negative_ratio, smile_rate)."""
    positive = sum(pct for e, pct in distribution.items() if e in _POSITIVE_EMOTIONS)
    neutral  = distribution.get("neutral", 0.0)
    negative = sum(pct for e, pct in distribution.items() if e in _NEGATIVE_EMOTIONS)
    return positive, neutral, negative, positive  # smile_rate == positive_ratio


def _calculate_stress_peaks(timeline: list[dict], min_run: int = 3) -> int:
    """Count runs of ≥ min_run consecutive negative-emotion frames as one 'peak'."""
    detected = [p for p in timeline if p.get("face_detected")]
    if not detected:
        return 0

    peaks   = 0
    run_len = 0
    in_peak = False

    for p in detected:
        is_negative = p.get("dominant_emotion", "") in _NEGATIVE_EMOTIONS
        if is_negative:
            run_len += 1
            if run_len >= min_run and not in_peak:
                peaks  += 1
                in_peak = True
        else:
            run_len = 0
            in_peak = False

    return peaks


# ── Public API ──────────────────────────────────────────────────────────────────

def analyze_emotions(
    emotion_results: list,
    video_fps:       float = 5.0,
) -> EmotionMetrics:
    if not emotion_results:
        return EmotionMetrics(emotion_distribution={})

    timeline = _build_timeline(emotion_results, video_fps)
    if not timeline:
        return EmotionMetrics(emotion_distribution={})

    distribution              = _calculate_emotion_distribution(timeline)
    dominant_emotion, dom_pct = _get_dominant_emotion(timeline)
    transitions, trans_rate   = _calculate_transitions(timeline)
    true_vol                  = _calculate_true_volatility(timeline)
    avg_conf                  = _calculate_avg_confidence(timeline)
    pos_pct, neu_pct, neg_pct, smile = _calculate_ratios(distribution)
    stress_peaks              = _calculate_stress_peaks(timeline)

    detected_count = sum(1 for p in timeline if p.get("face_detected"))
    logger.info(
        "[EmotionMetrics] %d frames, %d with face | dominant=%s (%.0f%%) "
        "| true_volatility=%.1f | positive=%.0f%% | stress_peaks=%d",
        len(timeline), detected_count, dominant_emotion, dom_pct,
        true_vol, pos_pct, stress_peaks,
    )

    return EmotionMetrics(
        emotion_distribution= distribution,
        dominant_emotion=     dominant_emotion,
        dominant_emotion_pct= dom_pct,
        emotion_timeline=     timeline,
        emotion_transitions=  transitions,
        transition_rate=      trans_rate,
        true_volatility=      true_vol,
        emotion_confidence=   avg_conf * 100.0,
        positive_ratio=       pos_pct,
        neutral_ratio=        neu_pct,
        negative_ratio=       neg_pct,
        smile_rate=           smile,
        stress_peak_count=    stress_peaks,
    )
