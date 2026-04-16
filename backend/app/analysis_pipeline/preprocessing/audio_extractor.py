import os
import subprocess
import tempfile
from pathlib import Path

AUDIO_ONLY_FORMATS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}


def extract_audio(video_path: str) -> tuple[str, bool]:
    """
    Extract audio track from a video file as a 16kHz mono mp3.

    Returns:
        (audio_path, is_temp) — if is_temp is True, caller must delete the file.

    If the input is already a pure audio format, returns it unchanged
    with is_temp=False so the caller never tries to delete the original.
    """
    suffix = Path(video_path).suffix.lower()

    if suffix in AUDIO_ONLY_FORMATS:
        return video_path, False

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    audio_path = tmp.name

    result = subprocess.run(
        [
            "ffmpeg",
            "-i",   video_path,
            "-vn",              
            "-ar",  "16000",    
            "-ac",  "1",        
            "-q:a", "4",        
            audio_path,
            "-y",               
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # clean up the empty temp file before raising
        try:
            os.unlink(audio_path)
        except OSError:
            pass
        raise RuntimeError(
            f"ffmpeg audio extraction failed:\n{result.stderr}"
        )

    return audio_path, True