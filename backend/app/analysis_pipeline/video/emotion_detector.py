"""
Emotion Detector
================
Frame-by-frame emotion detection following the proven pipeline from
"Frame-by-Frame: Tracking Emotions in Videos with AI" (Legara, 2023):

    MTCNN.detect() → PIL crop → AutoFeatureExtractor → ViT → softmax

Critical fix vs previous version
---------------------------------
The old code called ``mtcnn(image)`` which returns a *normalized face tensor*
suitable for FaceNet embeddings, then fed that tensor directly to the ViT model.
The ViT model expects pixel values preprocessed by its own AutoFeatureExtractor
— the old path silently produced garbage probabilities.

Correct path (this file)
  1. mtcnn.detect(pil_image)  → bounding boxes
  2. pil_image.crop(box)      → PIL face crop
  3. extractor(images=crop)   → pixel_values tensor
  4. model(**inputs)          → logits
  5. softmax(logits)          → per-emotion probabilities (0-1 each, sum to 1)

Batch processing
-----------------
MTCNN and AutoFeatureExtractor both accept lists of images, so we process
all sampled frames in a single GPU pass when possible (``batch_size`` controls
chunk size to stay within VRAM).

Outputs
-------
Each ``EmotionDetectionResult`` stores:
  - emotion_scores   : dict[emotion → probability 0-1]
  - dominant_emotion : emotion with highest probability
  - confidence       : max probability (0-1)
  - face_detected    : bool
  - frame_index      : original frame index (for timestamp → frame_idx / fps)

Models
------
  Face detection  : MTCNN (facenet_pytorch), keep_all=False (one face / frame)
  Emotion         : trpakov/vit-face-expression (7 classes)
  Classes         : angry, disgust, fear, happy, neutral, sad, surprise
"""

import torch
import numpy as np
from PIL import Image
from functools import lru_cache

from facenet_pytorch import MTCNN
from transformers import (
    AutoFeatureExtractor,
    AutoModelForImageClassification,
    AutoConfig,
)


# ── Constants ──────────────────────────────────────────────────────────────────

EMOTION_CLASSES = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

_MODEL_ID = "trpakov/vit-face-expression"

# MTCNN parameters from the article (tuned for interview-distance faces)
_MTCNN_MIN_FACE = 40          # lowered from 200: interview faces can be small
_MTCNN_THRESHOLDS = [0.6, 0.7, 0.7]
_MTCNN_FACTOR = 0.709


# ── Model cache ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_models(device: str = "cpu"):
    """Load and cache MTCNN + ViT feature extractor + ViT model.

    Called lazily on first use; subsequent calls hit the LRU cache.
    """
    mtcnn = MTCNN(
        image_size=160,
        margin=0,
        min_face_size=_MTCNN_MIN_FACE,
        thresholds=_MTCNN_THRESHOLDS,
        factor=_MTCNN_FACTOR,
        post_process=True,
        keep_all=False,   # one dominant face per frame
        device=device,
    )

    extractor = AutoFeatureExtractor.from_pretrained(_MODEL_ID)

    model = AutoModelForImageClassification.from_pretrained(_MODEL_ID)
    model = model.to(device)
    model.eval()

    # Cache the id→label mapping too (avoids repeated config loads)
    id2label = AutoConfig.from_pretrained(_MODEL_ID).id2label

    return mtcnn, extractor, model, id2label


# ── Result class ────────────────────────────────────────────────────────────────

class EmotionDetectionResult:
    """Emotion detection result for a single video frame."""

    __slots__ = (
        "emotion_scores", "dominant_emotion", "confidence",
        "face_detected", "frame_index",
    )

    def __init__(
        self,
        emotion_scores: dict[str, float] | None = None,
        face_detected: bool = False,
        confidence: float = 0.0,
        frame_index: int = 0,
    ):
        self.emotion_scores   = emotion_scores or {e: 0.0 for e in EMOTION_CLASSES}
        self.face_detected    = face_detected
        self.confidence       = confidence       # max probability (0-1)
        self.frame_index      = frame_index

        if emotion_scores and face_detected:
            self.dominant_emotion = max(emotion_scores, key=emotion_scores.get)
        else:
            self.dominant_emotion = "neutral"


# ── Single-frame detection ──────────────────────────────────────────────────────

def detect_frame_emotion(
    frame: np.ndarray,
    device: str      = "cpu",
    frame_index: int = 0,
) -> EmotionDetectionResult:
    """Detect emotions in a single BGR video frame (numpy uint8).

    Implements the exact pipeline from Legara (2023):
      MTCNN.detect → PIL crop → feature extractor → ViT → softmax
    """
    mtcnn, extractor, model, id2label = _load_models(device=device)

    try:
        # BGR (OpenCV) → RGB (PIL)
        frame_rgb = np.ascontiguousarray(frame[:, :, ::-1]).astype(np.uint8)
        pil_image = Image.fromarray(frame_rgb)

        # ── Step 1: detect bounding box ───────────────────────────────────
        with torch.no_grad():
            boxes, probs_mtcnn = mtcnn.detect(pil_image)

        if boxes is None or len(boxes) == 0:
            return EmotionDetectionResult(frame_index=frame_index)

        box = boxes[0]   # first (most prominent) face

        # ── Step 2: crop face from PIL image ──────────────────────────────
        face_pil = pil_image.crop(box)

        # ── Step 3: feature extractor preprocessing ───────────────────────
        inputs = extractor(images=face_pil, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # ── Step 4: ViT forward pass ──────────────────────────────────────
        with torch.no_grad():
            outputs = model(**inputs)
            probs   = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]

        # ── Step 5: map to emotion labels ─────────────────────────────────
        emotion_scores = {
            id2label[i]: float(probs[i].cpu())
            for i in range(len(probs))
        }

        max_conf = float(max(emotion_scores.values()))

        return EmotionDetectionResult(
            emotion_scores=emotion_scores,
            face_detected=True,
            confidence=max_conf,
            frame_index=frame_index,
        )

    except Exception as exc:
        print(f"[EmotionDetector] frame {frame_index} failed: {exc}")
        return EmotionDetectionResult(frame_index=frame_index)


# ── Batch video detection ───────────────────────────────────────────────────────

def detect_video_emotions(
    frames:      list[np.ndarray],
    frame_skip:  int = 1,
    device:      str = "cpu",
    batch_size:  int = 16,
) -> list[EmotionDetectionResult]:
    """Detect emotions for every sampled frame in a video.

    Processes frames in batches through MTCNN and ViT for GPU efficiency.

    Args:
        frames     : list of BGR numpy uint8 arrays (from cv2 / extract_frames)
        frame_skip : use every Nth frame (1 = use all — upstream already sampled)
        device     : "cpu" or "cuda"
        batch_size : number of frames per ViT batch (tune to VRAM)

    Returns:
        List of EmotionDetectionResult, one per *sampled* frame, in order.
    """
    mtcnn, extractor, vit_model, id2label = _load_models(device=device)

    # Collect sampled frames with their original indices
    sampled: list[tuple[int, np.ndarray]] = [
        (i, frames[i])
        for i in range(0, len(frames), frame_skip)
    ]

    results: list[EmotionDetectionResult] = []

    for chunk_start in range(0, len(sampled), batch_size):
        chunk = sampled[chunk_start: chunk_start + batch_size]

        # Convert BGR → RGB PIL images
        pil_images = [
            Image.fromarray(np.ascontiguousarray(f[:, :, ::-1]).astype(np.uint8))
            for _, f in chunk
        ]

        # ── Batch face detection ──────────────────────────────────────────
        try:
            with torch.no_grad():
                batch_boxes, _ = mtcnn.detect(pil_images)
        except Exception as exc:
            print(f"[EmotionDetector] MTCNN batch failed (chunk {chunk_start}): {exc}")
            batch_boxes = None

        # Normalise: MTCNN may return a numpy array (all-face batch) or a list
        # (mixed None/array batch). Either way we need a plain Python list so
        # that `if batch_boxes is not None` works without "ambiguous truth value".
        if batch_boxes is None:
            boxes_list: list = [None] * len(chunk)
        elif isinstance(batch_boxes, np.ndarray):
            # shape (batch, 4) when keep_all=False and all images have a face
            boxes_list = [batch_boxes[i] for i in range(len(batch_boxes))]
        else:
            boxes_list = list(batch_boxes)

        # ── Collect valid face crops ──────────────────────────────────────
        valid_indices: list[int]       = []   # position within chunk
        face_crops:   list[Image.Image] = []

        for pos, ((orig_idx, _), pil_img, boxes) in enumerate(
            zip(chunk, pil_images, boxes_list)
        ):
            if boxes is None:
                continue
            # boxes is either:
            #   1D ndarray shape (4,)   — keep_all=False selected best face
            #   2D ndarray shape (n, 4) — keep_all=True  (we take index 0)
            boxes_arr = np.asarray(boxes)
            if boxes_arr.ndim == 1:
                coords = boxes_arr          # already (x1,y1,x2,y2)
            elif boxes_arr.ndim == 2 and len(boxes_arr) > 0:
                coords = boxes_arr[0]       # first/best face row
            else:
                continue

            # PIL.crop expects integer pixel coordinates
            x1, y1, x2, y2 = (int(round(float(c))) for c in coords[:4])
            if x2 <= x1 or y2 <= y1:
                continue

            face_crops.append(pil_img.crop((x1, y1, x2, y2)))
            valid_indices.append(pos)

        # Pre-fill results with "no face" defaults
        chunk_results: list[EmotionDetectionResult] = [
            EmotionDetectionResult(frame_index=orig_idx)
            for orig_idx, _ in chunk
        ]

        # ── Batch ViT inference on valid crops ────────────────────────────
        if face_crops:
            try:
                inputs = extractor(images=face_crops, return_tensors="pt")
                inputs = {k: v.to(device) for k, v in inputs.items()}

                with torch.no_grad():
                    outputs = vit_model(**inputs)
                    all_probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

                for rank, pos in enumerate(valid_indices):
                    probs_row   = all_probs[rank].cpu()
                    orig_idx    = chunk[pos][0]
                    emotion_scores = {
                        id2label[i]: float(probs_row[i])
                        for i in range(len(probs_row))
                    }
                    max_conf = float(probs_row.max())
                    chunk_results[pos] = EmotionDetectionResult(
                        emotion_scores=emotion_scores,
                        face_detected=True,
                        confidence=max_conf,
                        frame_index=orig_idx,
                    )

            except Exception as exc:
                print(f"[EmotionDetector] ViT batch failed (chunk {chunk_start}): {exc}")
                # Fall through — chunk_results already has "no face" defaults

        results.extend(chunk_results)

    detected = sum(1 for r in results if r.face_detected)
    print(
        f"[EmotionDetector] {len(results)} frames analyzed, "
        f"{detected} faces detected ({detected/max(len(results),1)*100:.0f}%)"
    )
    return results
