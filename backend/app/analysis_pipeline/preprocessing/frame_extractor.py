import cv2
import numpy as np

from app.config import settings  # noqa: E402


def extract_frames(
    video_path:  str,
    fps_target:  int = 5,
) -> list[tuple[float, np.ndarray]]:
    """
    Extract frames at a fixed target FPS from the video.
    Default 5 frames per second for interview analysis while keeping
    CPU cost manageable.

    Frames are capped at settings.video_max_frames to prevent OOM on very long
    recordings.  VFR (variable frame-rate) videos may produce slightly uneven
    timestamps; the fallback `frame_index / src_fps` handles the edge case where
    OpenCV reports negative timestamps.

    Returns list of (timestamp_seconds, frame_numpy_array).
    """
    cap = cv2.VideoCapture(video_path)
    src_fps     = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    if src_fps <= 0:
        cap.release()
        raise RuntimeError(f"Cannot read FPS from video: {video_path}")

    target_fps      = max(1.0, float(fps_target))
    sample_interval = 1.0 / target_fps
    next_sample_ts  = 0.0

    frames: list[tuple[float, np.ndarray]] = []
    last_emitted_ts = -1.0
    frame_index     = 0
    max_frames      = getattr(settings, "video_max_frames", 2_000)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if frame_ts < 0:
            frame_ts = frame_index / src_fps

        if frame_ts + (sample_interval * 0.25) >= next_sample_ts:
            if frame_ts != last_emitted_ts:
                frames.append((round(frame_ts, 3), frame))
                last_emitted_ts = frame_ts
                if len(frames) >= max_frames:
                    break
            next_sample_ts += sample_interval

        frame_index += 1

    cap.release()
    video_duration = frame_count / src_fps if frame_count > 0 else len(frames) / max(src_fps, 1)
    print(
        f"[Video] Extracted {len(frames)} frames at {fps_target}fps "
        f"from {video_duration:.1f}s video (cap: {max_frames})"
    )
    return frames
