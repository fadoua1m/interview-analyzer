"""
Video Analysis Module
=====================
Efficient frame-by-frame analysis:
  - emotion_detector: ViT-Face-Expression emotion detection
  - engagement_analyzer: Head stability + gaze consistency metrics
  - emotion_metrics: Emotion distribution, transitions, volatility
  - video_analyzer: Main orchestrator

Models:
  - Face Detection: MTCNN (facenet_pytorch)
  - Emotion Classification: ViT-Face-Expression (transformers)

Removed: cheating_detector

Entry Point:
  - analyze_video(video_path): Main function
  - analyze_video_frames(frames): For preprocessed frames
"""

# Main entry point
from app.analysis_pipeline.video.video_analyzer import (
    analyze_video,
    analyze_video_frames,
    VideoAnalysisResult,
)

# Individual analyzers
from app.analysis_pipeline.video.emotion_detector import (
    detect_frame_emotion,
    detect_video_emotions,
    EmotionDetectionResult,
    EMOTION_CLASSES,
)

from app.analysis_pipeline.video.engagement_analyzer import (
    analyze_engagement,
    EngagementMetrics,
)

from app.analysis_pipeline.video.emotion_metrics import (
    analyze_emotions,
    EmotionMetrics,
)

__all__ = [
    # Main entry point
    "analyze_video",
    "analyze_video_frames",
    "VideoAnalysisResult",
    
    # Emotion Detection
    "detect_frame_emotion",
    "detect_video_emotions",
    "EmotionDetectionResult",
    "EMOTION_CLASSES",
    
    # Engagement
    "analyze_engagement",
    "EngagementMetrics",
    
    # Emotion Metrics
    "analyze_emotions",
    "EmotionMetrics",
]