import os
import re
from pathlib import Path

from groq import Groq
from app.config import settings
from app.analysis_pipeline.preprocessing.audio_extractor import extract_audio

_client = Groq(api_key=settings.groq_api_key)


def _remove_timestamps(text: str) -> str:
    return re.sub(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', '', text)


def _remove_fillers(text: str) -> str:
    fillers = [re.escape(token) for token in settings.transcript_fillers_list]
    if not fillers:
        return text
    pattern = r'\b(' + '|'.join(fillers) + r')\b'
    return re.sub(pattern, '', text, flags=re.IGNORECASE)


def _remove_repetitions(text: str) -> str:
    return re.sub(r'\b(.{10,}?)\s+\1\b', r'\1', text, flags=re.IGNORECASE)


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
    # _remove_repetitions intentionally omitted: the regex matched meaningful
    # repeated content (e.g. restated examples) and corrupted answers.
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def transcribe(video_path: str) -> dict:
    audio_path, is_temp = extract_audio(video_path)

    try:
        with open(audio_path, "rb") as f:
            language = settings.whisper_language.strip().lower()
            language_value = None if language in {"", "auto"} else language

            request_kwargs = {
                "file": (Path(audio_path).name, f),
                "model": settings.whisper_model,
                "response_format": "verbose_json",
                "timestamp_granularities": ["segment"],
                "temperature": 0.0,
            }
            if language_value:
                request_kwargs["language"] = language_value

            response = _client.audio.transcriptions.create(**request_kwargs)
    except Exception:
        if is_temp:
            try:
                os.unlink(audio_path)
            except OSError:
                pass
        raise

    raw_text   = response.text
    clean_text = clean_transcript(raw_text)

    print(f"[Transcribe] raw:   {len(raw_text)} chars")
    print(f"[Transcribe] clean: {len(clean_text)} chars")

    raw_segments = response.segments or []
    segments_out: list[dict] = []
    for seg in raw_segments:
        try:
            # Groq SDK returns Pydantic objects — use attribute access.
            # Fall back to dict-style in case a future SDK version changes this.
            if isinstance(seg, dict):
                start, end, text = seg["start"], seg["end"], seg["text"]
            else:
                start, end, text = seg.start, seg.end, seg.text
            if text and str(text).strip():
                segments_out.append({"start": float(start), "end": float(end), "text": str(text).strip()})
        except Exception:
            pass  # malformed segment — skip silently

    print(f"[Transcribe] segments: {len(segments_out)}")

    return {
        "text":         raw_text,
        "clean_text":   clean_text,
        "language":     getattr(response, "language", None),
        "segments":     segments_out,
        "audio_path":   audio_path,
        "audio_is_temp": is_temp,
    }