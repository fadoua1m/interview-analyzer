import logging
import os
from concurrent.futures import ThreadPoolExecutor

from app.analysis_pipeline.preprocessing.transcriber import transcribe
from app.analysis_pipeline.preprocessing.segmenter import segment_transcript
from app.analysis_pipeline.preprocessing.frame_extractor import extract_frames
from app.analysis_pipeline.text import analyze_text, TextAnalysisResult
from app.analysis_pipeline.video import analyze_video_frames, VideoAnalysisResult
from app.analysis_pipeline.report_assembler import assemble
from app.schemas.analysis import AnalysisRequest, Report

logger = logging.getLogger(__name__)


# ── Preprocessing orchestrator ────────────────────────────────────────────────

def _run_preprocessing(video_url: str, questions: list):
    """
    Run audio transcription and frame extraction in parallel, then segment.

    Returns:
        transcription_result : dict  {"clean_text", "audio_path", "audio_is_temp", ...}
        qa_pairs             : list[QAPair]
        frames               : list[np.ndarray]
        video_fps            : float
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        f_audio  = executor.submit(transcribe,     video_url)
        f_frames = executor.submit(extract_frames, video_url)
    # executor.shutdown(wait=True) is called on with-block exit — both futures
    # are guaranteed done here; result() is non-blocking from this point.

    transcription_result = f_audio.result()
    clean_text           = transcription_result.get("clean_text", "")
    whisper_segments     = transcription_result.get("segments") or []

    qa_pairs = segment_transcript(clean_text, questions, transcript_segments=whisper_segments)

    raw_frames: list[tuple[float, object]] = f_frames.result() or []
    frames = [frame for _ts, frame in raw_frames]

    if len(raw_frames) >= 2:
        span      = raw_frames[-1][0] - raw_frames[0][0]
        video_fps = round(len(raw_frames) / span, 2) if span > 0 else 5.0
    else:
        video_fps = 5.0

    return transcription_result, qa_pairs, frames, video_fps


# ── Main entry point ──────────────────────────────────────────────────────────

def run_analysis(request: AnalysisRequest) -> Report:
    """
    Main analysis pipeline.

    Flow:
      1. PREPROCESSING : transcribe + extract frames (parallel), then segment
      2. ANALYSIS      : text & video analysis (parallel)
      3. REPORT        : assemble final report
    """
    text_result:  TextAnalysisResult | None = None
    video_result: VideoAnalysisResult | None = None
    transcription_result = {}

    try:
        # ── Phase 1: Preprocessing ────────────────────────────────────────────
        logger.info("[Pipeline] Starting preprocessing...")
        transcription_result, qa_pairs, frames, video_fps = _run_preprocessing(
            request.video_url, request.questions
        )
        logger.info(
            "[Pipeline] Preprocessing complete: %d Q&A pairs, %d frames @ %.1f fps",
            len(qa_pairs), len(frames), video_fps,
        )

        # ── Phase 2: Parallel text & video analysis ───────────────────────────
        logger.info("[Pipeline] Starting parallel text & video analysis...")
        with ThreadPoolExecutor(max_workers=2) as executor:
            f_text  = executor.submit(analyze_text, qa_pairs, None)
            f_video = executor.submit(analyze_video_frames, frames, video_fps, 1)
        # Both futures are done after the with-block exits.

        try:
            text_result = f_text.result()
            logger.info(
                "[Pipeline] Text analysis complete: clarity=%.1f confidence=%s",
                text_result.overall_clarity, text_result.overall_confidence,
            )
        except Exception as exc:
            logger.error("[Pipeline] Text analysis failed: %s", exc)

        try:
            video_result = f_video.result()
            logger.info(
                "[Pipeline] Video analysis complete: engagement=%.0f%% emotion=%s",
                video_result.engagement_metrics.engagement_rate,
                video_result.emotion_metrics.dominant_emotion,
            )
        except Exception as exc:
            logger.error("[Pipeline] Video analysis failed: %s", exc)

        # ── Phase 3: Report Assembly ──────────────────────────────────────────
        logger.info("[Pipeline] Assembling final report...")
        report = assemble(
            interview_id=request.interview_id,
            qa_pairs=qa_pairs,
            text_result=text_result,
            video_result=video_result,
        )
        logger.info("[Pipeline] Analysis complete.")
        return report

    finally:
        if transcription_result.get("audio_is_temp"):
            audio_path = transcription_result.get("audio_path")
            if audio_path and os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                    logger.debug("[Pipeline] Cleaned up temp audio: %s", audio_path)
                except OSError as exc:
                    logger.warning("[Pipeline] Could not clean up audio: %s", exc)
