"""
Clarity Analyzer
================
Evaluates answer clarity, structural quality, and language confidence
from an HR recruiter's perspective.

Returns per-answer ClarityAnalysis with:
  - clarity_score  (0-10) : structural coherence and communicative quality
  - confidence_level       : high | medium | low (language ownership signals)
  - star_coverage          : full | partial | missing (STAR method presence)
  - brief_justification    : one sentence recruiter note
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.config                  import settings
from app.schemas.analysis        import QAPair
from app.services.mistral_client import generate_json

_NO_ANSWER_PLACEHOLDER = "[No answer extracted]"


# ── Prompt ─────────────────────────────────────────────────────────────────────

_CLARITY_PROMPT = """You are a senior HR talent assessor evaluating a candidate's spoken interview answer.
Your task: assess CLARITY, STRUCTURE, and LANGUAGE CONFIDENCE.

---
QUESTION ASKED:
{question}

CANDIDATE'S ANSWER:
{answer}
---

## TASK 1 — Clarity Score (0-10)
Evaluate how clearly and coherently the candidate communicates.

Scoring rubric:
  9-10  Excellent — Crystal-clear, well-organized, concise. Idea flows logically from context → point → outcome. No filler or rambling.
  7-8   Good      — Clear and mostly structured. Minor tangents or slight verbosity, but the main idea is easy to follow.
  5-6   Average   — Understandable but disorganized. Jumps between points, uses filler phrases, or leaves key ideas incomplete.
  3-4   Weak      — Difficult to follow. Lots of repetition, unclear transitions, or the answer drifts far from the question.
  0-2   Poor      — Incoherent, near-empty, or completely off-structure. No discernible logic.

Penalize for: excessive filler words ("um", "like", "you know"), circular reasoning, answering a different question, repeating the same point.
Reward for: concise framing, logical flow (context → action → outcome), precise vocabulary.

## TASK 2 — Language Confidence
Decide ONE level based on word-choice and ownership patterns:

  "high"   → Candidate uses first-person decisive verbs ("I led", "I designed", "I delivered", "I achieved").
              States outcomes as facts, not possibilities. No hedging. Takes ownership of successes AND failures.
  "medium" → Mostly clear but includes hedging ("I think", "probably", "we kind of did").
              Uses "we" without clarifying personal role. Avoids being concrete about outcomes.
  "low"    → Heavy hedging ("maybe", "I'm not sure", "sort of", "hopefully").
              Passive voice throughout. Avoids accountability. Vague on personal contribution.

## TASK 3 — STAR Method Coverage
Does the answer follow the STAR method (Situation → Task → Action → Result)?

  "full"    → All 4 STAR elements are clearly present.
  "partial" → 2 or 3 STAR elements are present (common: Situation+Action but no Result).
  "missing" → 0 or 1 element (just an opinion, a claim, or a generic statement).

## TASK 4 — Brief Recruiter Note
One concise sentence (max 15 words) summarizing the communication quality for an HR report.

Return ONLY valid JSON (no markdown, no extra text):
{{
  "clarity_score": 7.5,
  "confidence_level": "medium",
  "star_coverage": "partial",
  "brief_justification": "Candidate communicates clearly but lacks a measurable outcome in this answer."
}}
"""


# ── Result class ───────────────────────────────────────────────────────────────

class ClarityAnalysis:
    """Per-answer clarity analysis result."""

    VALID_CONFIDENCE = {"high", "medium", "low"}
    VALID_STAR       = {"full", "partial", "missing"}

    def __init__(
        self,
        clarity_score:      float = 5.0,
        confidence_level:   str   = "medium",
        star_coverage:      str   = "partial",
        brief_justification:str   = "",
        skipped:            bool  = False,
    ):
        self.clarity_score       = round(max(0.0, min(10.0, float(clarity_score))), 2)
        self.confidence_level    = confidence_level    if confidence_level    in self.VALID_CONFIDENCE else "medium"
        self.star_coverage       = star_coverage       if star_coverage       in self.VALID_STAR       else "partial"
        self.brief_justification = str(brief_justification).strip()[:200]
        self.skipped             = skipped  # True when answer was absent/placeholder


# ── Per-pair worker ────────────────────────────────────────────────────────────

def _analyze_one(pair: QAPair, language: str = "en") -> ClarityAnalysis:
    answer = (pair.answer or "").strip()
    answer_words = len(answer.split()) if answer else 0
    
    print(f"[Clarity] Processing Q: {pair.question[:50]}... | Answer: {answer[:60]}... | Words: {answer_words}")
    
    is_placeholder = answer == settings.segment_no_answer_placeholder
    if not answer or is_placeholder or answer_words < settings.text_min_answer_words:
        reason = "No answer was extracted from the transcript." if is_placeholder else f"Answer too short ({answer_words} words)."
        print(f"[Clarity] SKIPPED: {reason}")
        return ClarityAnalysis(
            clarity_score=0.0,
            confidence_level="low",
            star_coverage="missing",
            brief_justification=reason,
            skipped=True,
        )

    print(f"[Clarity] ✓ Calling LLM for evaluation...")
    prompt = _CLARITY_PROMPT.format(
        question=pair.question.strip(),
        answer=answer[:3000],
    )

    try:
        data = generate_json(prompt)
        result = ClarityAnalysis(
            clarity_score=      float(data.get("clarity_score",      5.0)),
            confidence_level=   str(data.get("confidence_level",     "medium")).strip().lower(),
            star_coverage=      str(data.get("star_coverage",        "partial")).strip().lower(),
            brief_justification=str(data.get("brief_justification",  "")),
        )
        print(f"[Clarity] ✓ LLM returned: score={result.clarity_score}")
        return result
    except Exception as e:
        print(f"[Clarity] ❌ LLM ERROR: {e}")
        return ClarityAnalysis()


# ── Public API ─────────────────────────────────────────────────────────────────

def run(qa_pairs: list[QAPair], language: str = "en") -> list[ClarityAnalysis]:
    """Analyze clarity for all QA pairs in parallel.
    Returns a list aligned 1-to-1 with qa_pairs. Never raises.
    """
    if not qa_pairs:
        return []

    results: list[ClarityAnalysis | None] = [None] * len(qa_pairs)
    max_workers = min(len(qa_pairs), settings.text_relevance_max_workers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_analyze_one, p, language): i for i, p in enumerate(qa_pairs)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
                print(f"[Clarity] Q{idx + 1}: score={results[idx].clarity_score}, conf={results[idx].confidence_level}")
            except Exception as e:
                print(f"[Clarity] Q{idx + 1} failed: {e}")
                results[idx] = ClarityAnalysis()

    return [r if r is not None else ClarityAnalysis() for r in results]
