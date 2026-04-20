import json
import logging
import re

from app.config import settings
from app.services.mistral_client import generate
from app.schemas.analysis import QAPair, QuestionInput

logger = logging.getLogger(__name__)


_SEGMENT_PROMPT = """You are given a job interview transcript and a numbered list of questions that were asked.
The interview can be in English or French.

CRITICAL RULES:
1. The questions may have been asked in ANY ORDER during the interview — match each answer to its question by SEMANTIC CONTENT, not by sequence position.
2. You MUST return EXACTLY {n_questions} items in the JSON array — one entry per question index (0 to {n_questions_minus_1}).
3. If you cannot find an answer for a question, return an empty string "" for "answer" — do NOT omit the entry.
4. NEVER merge two separate answers into one entry. Every question gets its own distinct, non-overlapping answer span.
5. When two consecutive answers discuss the same topic or project, use the CONTENT SHIFT as the boundary:
   - The first answer finishes its own narrative (reaches a natural conclusion or pause).
   - The second answer starts a new narrative thread, even if it references the same topic.
   - Use timestamps (if available) to identify the exact cut point.
6. Prefer shorter, precise extracts over long ones. If unsure where an answer ends, cut early rather than absorbing the next answer.
7. Preserve the original language of each answer verbatim.

Return ONLY a valid JSON array — no explanation, no markdown fences:
[
  {{"question_index": 0, "answer": "...", "start_sec": 0.0, "end_sec": 0.0}},
  ...
]

If you cannot identify where an answer starts or ends, use null for start_sec and end_sec.

Questions:
{questions}

Full transcript (with timestamps if available):
{transcript}"""


def segment_transcript(
    full_transcript: str,
    questions:       list[QuestionInput],
    transcript_segments: list[dict] | None = None,
) -> list[QAPair]:
    """
    Uses the configured LLM to split the full transcript into per-question answers.
    Falls back to sentence-aware chunking if parsing fails.

    Args:
        full_transcript:     Clean text transcript (used as fallback).
        questions:           Ordered list of QuestionInput objects.
        transcript_segments: Optional list of Whisper segments
                             [{"start": float, "end": float, "text": str}, ...].
                             When provided, the timestamped format is used in the
                             prompt, giving the LLM much stronger boundary signals.
    """
    print(f"[Segment] Full transcript length: {len(full_transcript)} chars")

    questions_fmt = "\n".join(
        f"{i}. {q.text}" for i, q in enumerate(questions)
    )

    # Build the transcript text to pass to the LLM.
    # Prefer the timestamped Whisper segments when available — they let the LLM
    # identify exactly where each answer starts and ends.
    if transcript_segments:
        timestamped_lines = [
            f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text'].strip()}"
            for seg in transcript_segments
            if seg.get("text", "").strip()
        ]
        transcript_text = "\n".join(timestamped_lines)
        print(f"[Segment] Using timestamped segments: {len(transcript_segments)} segments")
    else:
        transcript_text = full_transcript
        print(f"[Segment] WARNING: No timestamped segments available — using plain text (boundary detection degraded)")

    fitted_transcript = _fit_transcript_window(transcript_text)
    print(f"[Segment] Fitted transcript length: {len(fitted_transcript)} chars (max: {settings.segment_max_transcript_chars})")

    if len(fitted_transcript) < len(transcript_text):
        print(f"[Segment] WARNING: TRANSCRIPT TRUNCATED! {len(transcript_text) - len(fitted_transcript)} chars lost")

    n_questions = len(questions)
    prompt = _SEGMENT_PROMPT.format(
        n_questions=n_questions,
        n_questions_minus_1=n_questions - 1,
        questions=questions_fmt,
        transcript=fitted_transcript,
    )

    segments: list[dict] | None = None
    for attempt in range(settings.segment_llm_attempts):
        try:
            raw = generate(
                prompt if attempt == 0 else (
                    prompt + "\n\nReturn ONLY a JSON array. No prose, no markdown fences."
                )
            )
            candidate = _extract_json_array(raw)
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                segments = _normalize_segments(parsed, len(questions))
                print(f"[Segment] LLM successfully extracted {len(segments)} segments")
                break
        except Exception as e:
            print(f"[Segment] attempt {attempt + 1} failed: {e}")

    if segments is None:
        segments = _fallback_split(full_transcript, len(questions))
        print("[Segment] using fallback segmentation")

    # map segments back to questions preserving rubric + interview-level target skills
    pairs: list[QAPair] = []
    for i, q in enumerate(questions):
        match = next(
            (s for s in segments if s.get("question_index") == i), None
        )
        answer = match.get("answer", "") if match else ""
        answer = answer.strip() if isinstance(answer, str) else ""
        if not answer:
            print(f"[Segment] Q{i+1}: No answer found → using placeholder")
            answer = settings.segment_no_answer_placeholder
        else:
            print(f"[Segment] Q{i+1}: Extracted {len(answer)} chars")

        pairs.append(QAPair(
            question=      q.text,
            answer=        answer,
            rubric=        q.rubric,
            target_skills= q.target_skills,
            start_sec=     match.get("start_sec") if match else None,
            end_sec=       match.get("end_sec")   if match else None,
        ))

    return pairs


def _fit_transcript_window(transcript: str) -> str:
    text = (transcript or "").strip()
    if len(text) <= settings.segment_max_transcript_chars:
        return text

    budget = settings.segment_max_transcript_chars
    head = text[: budget // 2]
    tail = text[-(budget - len(head)) :]
    return f"{head}\n\n[... transcript truncated for length ...]\n\n{tail}"


def _normalize_segments(raw_segments: list[dict], question_count: int) -> list[dict]:
    if question_count <= 0:
        return []

    cleaned: list[dict] = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue

        # Normalise answer — treat None / non-string as empty string so that
        # the question_index is still preserved in the cleaned list.
        raw_answer = item.get("answer")
        if raw_answer is None:
            answer = ""
        elif not isinstance(raw_answer, str):
            answer = str(raw_answer).strip()
        else:
            answer = raw_answer.strip()

        idx = item.get("question_index")
        if isinstance(idx, str) and idx.isdigit():
            idx = int(idx)
        elif not isinstance(idx, int):
            idx = None

        # Always keep the entry — even when the answer is empty — so that
        # _assign_by_index can slot the placeholder at the correct index
        # rather than blindly pulling from the overflow bucket.
        cleaned.append({
            "question_index": idx,
            "answer": answer,  # may be "" → replaced with placeholder downstream
            "start_sec": item.get("start_sec"),
            "end_sec": item.get("end_sec"),
        })

    if not cleaned:
        return _fallback_split("", question_count)

    valid_index_count = sum(
        1
        for item in cleaned
        if isinstance(item.get("question_index"), int)
        and 0 <= item["question_index"] < question_count
    )

    if valid_index_count < max(1, len(cleaned) // 2):
        return _assign_sequentially(cleaned, question_count)

    return _assign_by_index(cleaned, question_count)


def _assign_sequentially(items: list[dict], question_count: int) -> list[dict]:
    output = []
    for i in range(question_count):
        if i < len(items):
            output.append({
                "question_index": i,
                "answer": items[i]["answer"],
                "start_sec": items[i].get("start_sec"),
                "end_sec": items[i].get("end_sec"),
            })
        else:
            output.append({
                "question_index": i,
                "answer": settings.segment_no_answer_placeholder,
                "start_sec": None,
                "end_sec": None,
            })

    if len(items) > question_count:
        overflow_text = "\n\n".join(item["answer"] for item in items[question_count:]).strip()
        if overflow_text:
            if output[-1]["answer"] == settings.segment_no_answer_placeholder:
                output[-1]["answer"] = overflow_text
            else:
                output[-1]["answer"] = f"{output[-1]['answer']}\n\n{overflow_text}".strip()

    return output


def _assign_by_index(items: list[dict], question_count: int) -> list[dict]:
    assigned: list[dict | None] = [None] * question_count
    overflow: list[dict] = []

    for item in items:
        idx = item.get("question_index")
        if isinstance(idx, int) and 0 <= idx < question_count and assigned[idx] is None:
            assigned[idx] = item
        else:
            overflow.append(item)

    # Fill unassigned slots with overflow.  Also allow a non-empty overflow item
    # to replace an empty-answer slot — the LLM may have returned a blank answer
    # with the right index while the real content landed in overflow without an index.
    for i in range(question_count):
        slot_empty = assigned[i] is None or not assigned[i].get("answer", "").strip()
        if slot_empty and overflow:
            # Prefer the first overflow item that has actual content.
            for j, ov in enumerate(overflow):
                if ov.get("answer", "").strip():
                    assigned[i] = overflow.pop(j)
                    break
            else:
                # No content-bearing overflow item; fall back to first available.
                if assigned[i] is None:
                    assigned[i] = overflow.pop(0)

    if overflow:
        # Only fill overflow into empty slots — never append to a populated slot,
        # as that would merge two different answers into the last question.
        extra = "\n\n".join(item["answer"] for item in overflow if item.get("answer", "").strip()).strip()
        if extra and (assigned[-1] is None or not assigned[-1].get("answer", "").strip()):
            assigned[-1] = {"answer": extra, "start_sec": None, "end_sec": None}

    output = []
    for i in range(question_count):
        item = assigned[i]
        answer = item.get("answer", "").strip() if item else ""
        output.append({
            "question_index": i,
            "answer": answer or settings.segment_no_answer_placeholder,
            "start_sec": item.get("start_sec") if item else None,
            "end_sec":   item.get("end_sec")   if item else None,
        })

    return output


def _fallback_split(transcript: str, n: int) -> list[dict]:
    if n <= 0:
        return []

    text = (transcript or "").strip()
    if text:
        logger.warning(
            "[Segment] FALLBACK: splitting %d chars of transcript into %d chunks by "
            "character count — answer-to-question mapping will likely be wrong. "
            "This only happens when the LLM failed all %d attempts.",
            len(text), n, settings.segment_llm_attempts,
        )
    if not text:
        return [
            {
                "question_index": i,
                "answer": settings.segment_no_answer_placeholder,
                "start_sec": None,
                "end_sec": None,
            }
            for i in range(n)
        ]

    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip()]
    if not sentences:
        sentences = [text]

    total_chars = sum(len(s) for s in sentences)
    target_chars = max(1, total_chars // n)

    chunks: list[str] = []
    current: list[str] = []
    current_chars = 0

    for sentence in sentences:
        if len(chunks) < n - 1 and current_chars >= target_chars and current:
            chunks.append(" ".join(current).strip())
            current = []
            current_chars = 0

        current.append(sentence)
        current_chars += len(sentence)

    if current:
        chunks.append(" ".join(current).strip())

    while len(chunks) < n:
        chunks.append(settings.segment_no_answer_placeholder)

    return [
        {
            "question_index": i,
            "answer": chunks[i],
            "start_sec": None,
            "end_sec": None,
        }
        for i in range(n)
    ]


def _extract_json_array(raw: str) -> str:
    text = raw.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    # Prefer extracting the outermost JSON array when the model adds prose.
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]

    return text