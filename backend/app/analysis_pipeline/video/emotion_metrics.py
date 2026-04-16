"""
Emotion Metrics
===============
Aggregates a sequence of EmotionDetectionResult objects into interview-level
emotion metrics, following the time-series analysis approach from
Legara (2023): store all 7 emotion probabilities per frame, then derive
distribution, transitions, volatility, and a rich timeline.

Timeline schema (per point):
  timestamp_sec    : float   — frame_index / video_fps
  dominant_emotion : str     — emotion with highest probability
  confidence       : float   — max probability (0-1)
  emotion_scores   : dict    — all 7 probabilities (like the article's DataFrame)
  face_detected    : bool

Volatility (corrected)
  = (emotion transitions between consecutive frames) / (total frames - 1) × 100
  NOT std-dev of confidence scores.
"""

import numpy as np
from collections import Counter


# ── EmotionMetrics class ────────────────────────────────────────────────────────

class EmotionMetrics:
    """Comprehensive interview-level emotion analysis metrics."""

    def __init__(
        self,
        emotion_distribution:  dict[str, float],  # % time in each emotion (0-100)
        dominant_emotion:      str   = "neutral",
        dominant_emotion_pct:  float = 0.0,
        emotion_timeline:      list[dict] | None = None,  # full frame-by-frame data
        emotion_transitions:   int   = 0,
        transition_rate:       float = 0.0,        # transitions per minute
        volatility_score:      float = 0.0,        # 0-100 (higher = more volatile)
        emotion_confidence:    float = 0.0,        # avg max-emotion confidence (0-100)
        positive_ratio:        float = 0.0,        # % frames showing happy / surprise
    ):
        self.emotion_distribution = emotion_distribution
        self.dominant_emotion     = dominant_emotion
        self.dominant_emotion_pct = round(max(0.0, min(100.0, dominant_emotion_pct)), 2)
        self.emotion_timeline     = emotion_timeline or []
        self.emotion_transitions  = emotion_transitions
        self.transition_rate      = round(transition_rate, 2)
        # Store confidence as 0-100 (constructor receives 0-1 value and scales it)
        self.emotion_confidence   = round(max(0.0, min(100.0, emotion_confidence * 100)), 2)
        self.volatility_score     = round(max(0.0, min(100.0, volatility_score)), 2)
        self.positive_ratio       = round(max(0.0, min(100.0, positive_ratio)), 2)


# ── Internal helpers ────────────────────────────────────────────────────────────

def _build_timeline(emotion_results: list, video_fps: float) -> list[dict]:
    """Convert EmotionDetectionResult list to timeline dicts with timestamps.

    Each dict follows the article's per-frame data model:
      {timestamp_sec, dominant_emotion, confidence, emotion_scores, face_detected}
    """
    timeline: list[dict] = []

    for result in emotion_results:
        if hasattr(result, "emotion_scores"):
            # Compute timestamp from stored frame_index (set during detection)
            frame_idx = getattr(result, "frame_index", len(timeline))
            ts        = round(frame_idx / max(video_fps, 1.0), 3)

            timeline.append({
                "timestamp_sec":    ts,
                "dominant_emotion": result.dominant_emotion,
                "confidence":       result.confidence,      # 0-1
                "emotion_scores":   result.emotion_scores,  # all 7 probs (0-1 each)
                "face_detected":    result.face_detected,
            })

        elif isinstance(result, dict):
            # Legacy / dict format — pass through
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
        1
        for prev, curr in zip(detected, detected[1:])
        if prev["dominant_emotion"] != curr["dominant_emotion"]
    )
    # transition rate: per minute using actual timestamps
    try:
        span_sec = detected[-1]["timestamp_sec"] - detected[0]["timestamp_sec"]
        rate     = (transitions / (span_sec / 60.0)) if span_sec > 0 else 0.0
    except (KeyError, ZeroDivisionError):
        rate = 0.0
    return transitions, round(rate, 2)


def _calculate_volatility(timeline: list[dict]) -> float:
    """Fraction of consecutive detected-frame pairs that change emotion × 100.

    0 = perfectly stable (never changes)
    100 = every frame switches emotion
    """
    detected = [p for p in timeline if p.get("face_detected")]
    n = len(detected)
    if n < 2:
        return 0.0
    transitions = sum(
        1
        for prev, curr in zip(detected, detected[1:])
        if prev["dominant_emotion"] != curr["dominant_emotion"]
    )
    return round((transitions / (n - 1)) * 100.0, 2)


def _calculate_avg_confidence(timeline: list[dict]) -> float:
    """Average max-emotion probability across detected frames (0-1 scale)."""
    confs = [p["confidence"] for p in timeline if p.get("face_detected") and "confidence" in p]
    return float(np.mean(confs)) if confs else 0.0


def _calculate_positive_ratio(distribution: dict[str, float]) -> float:
    """% of detected frames expressing happy or surprise."""
    return sum(pct for e, pct in distribution.items() if e in {"happy", "surprise"})


# ── Public API ──────────────────────────────────────────────────────────────────

def analyze_emotions(
    emotion_results: list,
    video_fps:       float = 5.0,
) -> EmotionMetrics:
    """Aggregate EmotionDetectionResult list into interview-level metrics.

    Args:
        emotion_results: list of EmotionDetectionResult objects (or legacy dicts)
        video_fps       : source FPS used to compute timestamps from frame_index.
                          If frames were extracted at 5 fps pass 5.0 (default).

    Returns:
        EmotionMetrics with full timeline, distribution, volatility, etc.
    """
    if not emotion_results:
        return EmotionMetrics(emotion_distribution={})

    # Build rich timeline with timestamps + all 7 probabilities
    timeline = _build_timeline(emotion_results, video_fps)

    if not timeline:
        return EmotionMetrics(emotion_distribution={})

    distribution              = _calculate_emotion_distribution(timeline)
    dominant_emotion, dom_pct = _get_dominant_emotion(timeline)
    transitions, trans_rate   = _calculate_transitions(timeline)
    volatility                = _calculate_volatility(timeline)
    avg_conf                  = _calculate_avg_confidence(timeline)
    positive_pct              = _calculate_positive_ratio(distribution)

    detected_count = sum(1 for p in timeline if p.get("face_detected"))
    print(
        f"[EmotionMetrics] {len(timeline)} frames, {detected_count} with face "
        f"| dominant={dominant_emotion} ({dom_pct:.0f}%) "
        f"| volatility={volatility:.0f} "
        f"| positive={positive_pct:.0f}%"
    )

    return EmotionMetrics(
        emotion_distribution= distribution,
        dominant_emotion=     dominant_emotion,
        dominant_emotion_pct= dom_pct,
        emotion_timeline=     timeline,
        emotion_transitions=  transitions,
        transition_rate=      trans_rate,
        volatility_score=     volatility,
        emotion_confidence=   avg_conf,   # will be ×100 in constructor
        positive_ratio=       positive_pct,
    )
