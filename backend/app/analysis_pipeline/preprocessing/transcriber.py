import logging
import os
import re
from pathlib import Path

from mistralai.client import Mistral
from app.config import settings
from app.analysis_pipeline.preprocessing.audio_extractor import extract_audio

logger = logging.getLogger(__name__)

_client = Mistral(api_key=settings.mistral_api_key)


def _remove_timestamps(text: str) -> str:
    return re.sub(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', '', text)


def _remove_fillers(text: str) -> str:
    fillers = [re.escape(token) for token in settings.transcript_fillers_list]
    if not fillers:
        return text
    pattern = r'\b(' + '|'.join(fillers) + r')\b'
    return re.sub(pattern, '', text, flags=re.IGNORECASE)


def _extract_candidate_speech(text: str) -> str:
    cues = [re.escape(token) for token in settings.transcript_interviewer_cues_list]
    if not cues:
        return text
    match = re.search(r'\b(?:' + '|'.join(cues) + r')\b', text, flags=re.IGNORECASE)
    if match and match.start() > settings.transcript_split_min_chars:
        return text[:match.start()].strip()
    return text


def clean_transcript(raw: str) -> str:
    text = _remove_timestamps(raw)
    text = _extract_candidate_speech(text)
    text = _remove_fillers(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def transcribe(video_path: str) -> dict:
    audio_path, is_temp = extract_audio(video_path)

    try:
        with open(audio_path, "rb") as f:
            language = settings.whisper_language.strip().lower()

            request_kwargs = {
                "model": "voxtral-mini-latest",
                "file":  {"file_name": Path(audio_path).name, "content": f},
            }
            if language not in {"", "auto"}:
                request_kwargs["language"] = language

            response = _client.audio.transcriptions.complete(**request_kwargs)

    except Exception:
        if is_temp:
            try:
                os.unlink(audio_path)
            except OSError:
                pass
        raise

    raw_text   = response.text or ""
    clean_text = clean_transcript(raw_text)

    logger.info("[Transcribe] raw:   %d chars", len(raw_text))
    logger.info("[Transcribe] clean: %d chars", len(clean_text))

    # Mistral returns segments on response.segments (list of dicts or objects)
    raw_segments = getattr(response, "segments", None) or []
    segments_out: list[dict] = []
    for seg in raw_segments:
        try:
            if isinstance(seg, dict):
                start, end, text = seg["start"], seg["end"], seg["text"]
            else:
                start, end, text = seg.start, seg.end, seg.text
            if text and str(text).strip():
                segments_out.append({
                    "start": float(start),
                    "end":   float(end),
                    "text":  str(text).strip(),
                })
        except Exception:
            pass

    logger.info("[Transcribe] segments: %d", len(segments_out))

    return {
        "text":          raw_text,
        "clean_text":    clean_text,
        "language":      getattr(response, "language", None),
        "segments":      segments_out,
        "audio_path":    audio_path,
        "audio_is_temp": is_temp,
    }
