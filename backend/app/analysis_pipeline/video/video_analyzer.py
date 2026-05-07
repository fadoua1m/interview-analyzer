"""
Video Analyzer
==============
Main orchestrator for video analysis:
  - Emotion detection (frame-by-frame using ViT-Face-Expression)
  - Engagement analysis (face presence, emotion stability, focus quality)
  - Emotion metrics and distribution

Notes:
  - ViT-Face-Expression does NOT provide head-pose or gaze data, so engagement
    is computed from face detection rate + emotion stability (no fabricated values).
  - Frames are sampled *during the read loop* to prevent OOM on long videos.
"""

import logging
import numpy as np
import cv2
from typing import Optional

logger = logging.getLogger(__name__)


class VideoAnalysisResult:
    """Complete video analysis output."""

    def __init__(
        self,
        duration_seconds:   float = 0.0,
        total_frames:       int   = 0,
        analyzed_frames:    int   = 0,
        video_fps:          float = 30.0,
        emotion_metrics           = None,   # EmotionMetrics
        engagement_metrics        = None,   # EngagementMetrics
    ):
        self.duration_seconds  = round(duration_seconds, 2)
        self.total_frames      = total_frames
        self.analyzed_frames   = analyzed_frames
        self.video_fps         = video_fps
        self.emotion_metrics   = emotion_metrics
        self.engagement_metrics= engagement_metrics


# ── Public API ─────────────────────────────────────────────────────────────────

def analyze_video(
    video_path: str,
    frame_skip: int = 5,
    device:     str = "cpu",
) -> VideoAnalysisResult:
    """Analyze a video file for emotions and engagement.

    Frames are sampled *during the read loop* (every ``frame_skip``-th frame)
    so memory stays bounded regardless of video length.

    Args:
        video_path : path to the video file
        frame_skip : keep 1 frame every N frames (default 5 ≈ 6 fps from 30 fps)
        device     : "cpu" or "cuda"
    """
    from app.analysis_pipeline.video.emotion_detector  import detect_video_emotions
    from app.analysis_pipeline.video.engagement_analyzer import analyze_engagement
    from app.analysis_pipeline.video.emotion_metrics    import analyze_emotions

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"[VideoAnalyzer] Cannot open video: {video_path}")

    fps          = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration     = total_frames / fps

    # Sample frames during read to keep memory bounded
    sampled_frames: list[np.ndarray] = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % frame_skip == 0:
            sampled_frames.append(frame)
        idx += 1
    cap.release()

    if not sampled_frames:
        raise ValueError(f"[VideoAnalyzer] No frames extracted from {video_path}")

    # Effective fps after skipping: frame_index / effective_fps = real timestamp
    effective_fps = fps / frame_skip

    logger.info(
        "[VideoAnalyzer] %d total frames → %d sampled (skip=%d, src_fps=%.1f, "
        "effective_fps=%.1f, duration=%.1fs)",
        total_frames, len(sampled_frames), frame_skip, fps, effective_fps, duration,
    )

    return _run_analysis(
        frames=sampled_frames,
        total_frames=total_frames,
        video_fps=effective_fps,   # used for timestamp = frame_index / fps
        device=device,
    )


def analyze_video_frames(
    frames:     list[np.ndarray],
    video_fps:  float = 30.0,
    frame_skip: int   = 1,
    device:     str   = "cpu",
) -> VideoAnalysisResult:
    """Analyze video from a pre-extracted list of frames.

    Used by the pipeline when frames have already been extracted and sampled
    by ``extract_frames()``.  Pass ``frame_skip=1`` (default) here because
    sampling already happened upstream; set higher if you want a second pass.

    Args:
        frames    : list of BGR numpy arrays
        video_fps : original video fps (used for transition-rate calculation)
        frame_skip: additional subsampling of the provided frames (default 1 = use all)
        device    : "cpu" or "cuda"
    """
    if not frames:
        raise ValueError("[VideoAnalyzer] No frames provided")

    duration = len(frames) / video_fps if video_fps > 0 else 0.0

    # Optional secondary subsampling
    sampled = frames if frame_skip <= 1 else frames[::frame_skip]

    return _run_analysis(
        frames=sampled,
        total_frames=len(frames),
        video_fps=video_fps,
        device=device,
    )


# ── Internal ───────────────────────────────────────────────────────────────────

def _run_analysis(
    frames:       list[np.ndarray],
    total_frames: int,
    video_fps:    float,
    device:       str,
) -> VideoAnalysisResult:
    """Shared analysis path for both entry points."""
    from app.analysis_pipeline.video.emotion_detector    import detect_video_emotions
    from app.analysis_pipeline.video.engagement_analyzer import analyze_engagement
    from app.analysis_pipeline.video.emotion_metrics     import analyze_emotions

    duration = total_frames / video_fps if video_fps > 0 else 0.0

    # ── Emotion detection ─────────────────────────────────────────────────────
    # frame_skip=1 here: caller already sampled; detector processes every frame
    emotion_results = detect_video_emotions(frames, frame_skip=1, device=device)

    # ── Build per-frame records (honest — no fabricated gaze/head-pose) ───────
    frame_records = [
        {
            "face_detected":   r.face_detected,
            "dominant_emotion":r.dominant_emotion,
            "emotion_scores":  r.emotion_scores,
            "confidence":      r.confidence,
        }
        for r in emotion_results
    ]

    # ── Engagement (from face presence + emotion stability only) ─────────────
    engagement_metrics = analyze_engagement(frame_records)

    # ── Emotion metrics ───────────────────────────────────────────────────────
    emotion_metrics = analyze_emotions(emotion_results, video_fps=video_fps)

    return VideoAnalysisResult(
        duration_seconds =duration,
        total_frames     =total_frames,
        analyzed_frames  =len(frames),
        video_fps        =video_fps,
        emotion_metrics  =emotion_metrics,
        engagement_metrics=engagement_metrics,
    )
