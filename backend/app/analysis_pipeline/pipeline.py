

import os
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

from app.analysis_pipeline.preprocessing.transcriber import transcribe
from app.analysis_pipeline.preprocessing.segmenter import segment_transcript
from app.analysis_pipeline.preprocessing.frame_extractor import extract_frames
from app.analysis_pipeline.text import analyze_text, TextAnalysisResult
from app.analysis_pipeline.video import analyze_video_frames, VideoAnalysisResult
from app.analysis_pipeline.report_assembler import assemble
from app.schemas.analysis import (
    AnalysisRequest,
    Report,
)


# ── Preprocessing orchestrator ────────────────────────────────────────────────

def _run_preprocessing(video_url: str, questions: list[dict]):
    """
    Preprocessing phase: Extract audio + transcribe + segment AND extract frames.

    Returns:
        transcription_result : dict  {"clean_text", "audio_path", "audio_is_temp", ...}
        qa_pairs             : list[QAPair]
        frames               : list[np.ndarray]  — timestamp stripped, ndarray only
        video_fps            : float             — source FPS reported by frame_extractor
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        f_audio  = executor.submit(transcribe,      video_url)
        f_frames = executor.submit(extract_frames,  video_url)
        wait([f_audio, f_frames], return_when=ALL_COMPLETED, timeout=300.0)

    transcription_result = f_audio.result()
    clean_text = transcription_result.get("clean_text", "")
    whisper_segments = transcription_result.get("segments") or []

    qa_pairs = segment_transcript(clean_text, questions, transcript_segments=whisper_segments)

    # extract_frames returns list[tuple[timestamp_sec, ndarray]] — unwrap
    raw_frames: list[tuple[float, object]] = f_frames.result() or []
    frames     = [frame for _ts, frame in raw_frames]

    # Infer source FPS from timestamps when available
    if len(raw_frames) >= 2:
        ts_last  = raw_frames[-1][0]
        ts_first = raw_frames[0][0]
        span     = ts_last - ts_first
        video_fps = round(len(raw_frames) / span, 2) if span > 0 else 5.0
    else:
        video_fps = 5.0   # frame_extractor default target fps

    return transcription_result, qa_pairs, frames, video_fps


# ── Main entry point ──────────────────────────────────────────────────────────

def run_analysis(request: AnalysisRequest) -> Report:
    """
    Main analysis pipeline.
    
    Flow:
      1. PREPROCESSING: Extract audio → transcribe → segment AND extract frames
      2. PARALLEL ANALYSIS: Video & Text analysis in parallel
      3. REPORT: Assemble final report
    """
    
    # Initialize safe defaults
    text_result: TextAnalysisResult | None = None
    video_result: VideoAnalysisResult | None = None
    transcription_result = {}
    qa_pairs = []
    
    try:
        # ── PHASE 1: Preprocessing ────────────────────────────────────────────
        print("[Pipeline] Starting preprocessing...")
        transcription_result, qa_pairs, frames, video_fps = _run_preprocessing(
            request.video_url, request.questions
        )
        print(f"[Pipeline] Preprocessing complete: {len(qa_pairs)} Q&A pairs, "
              f"{len(frames)} frames @ {video_fps} fps")

        # ── PHASE 2: Parallel Video & Text Analysis ──────────────────────────
        print("[Pipeline] Starting video & text analysis (parallel)...")
        with ThreadPoolExecutor(max_workers=2) as executor:
            # language=None → auto-detect from candidate answers
            f_text  = executor.submit(analyze_text, qa_pairs, None)
            # frames already sampled by extract_frames; frame_skip=1 = use all
            f_video = executor.submit(analyze_video_frames, frames,
                                      video_fps, 1)
            
            wait([f_text, f_video], return_when=ALL_COMPLETED, timeout=600.0)
        
        # Collect analysis results
        try:
            text_result = f_text.result(timeout=10)
            print(f"[Pipeline] Text analysis complete: clarity={text_result.overall_clarity}, "
                  f"confidence={text_result.overall_confidence}")
        except Exception as e:
            print(f"[Pipeline] Text analysis failed: {e}")
            text_result = None
        
        try:
            video_result = f_video.result(timeout=10)
            print(f"[Pipeline] Video analysis complete: engagement={video_result.engagement_metrics.engagement_rate}%, "
                  f"dominant_emotion={video_result.emotion_metrics.dominant_emotion}")
        except Exception as e:
            print(f"[Pipeline] Video analysis failed: {e}")
            video_result = None
        
        # ── PHASE 3: Report Assembly ─────────────────────────────────────────
        print("[Pipeline] Assembling final report...")
        report = assemble(
            interview_id=request.interview_id,
            qa_pairs=qa_pairs,
            text_result=text_result,
            video_result=video_result,
        )
        print(f"[Pipeline] Analysis complete. Report assembled.")
        
        return report
    
    finally:
        # Cleanup temporary audio file
        if transcription_result.get("audio_is_temp"):
            try:
                audio_path = transcription_result.get("audio_path")
                if audio_path and os.path.exists(audio_path):
                    os.unlink(audio_path)
                    print(f"[Pipeline] Cleaned up temporary audio: {audio_path}")
            except OSError as e:
                print(f"[Pipeline] Warning: could not clean up audio file: {e}")
