"""
Relevance Scorer
================
Scores how well each answer addresses its question (0-10 scale).

Two scoring modes:
  - Standard : question + answer only
  - Rubric   : question + recruiter rubric + answer (if rubric provided on QAPair)

Returns a dict {per_question: list[RelevanceScore], overall_score: float}
compatible with TextAnalysisResult.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.config                  import settings
from app.schemas.analysis        import QAPair
from app.services.mistral_client import generate_json


# ── Prompts ────────────────────────────────────────────────────────────────────

_RELEVANCE_PROMPT = """You are a senior HR talent assessor evaluating whether a candidate's answer
addresses the interview question asked.

---
QUESTION ASKED:
{question}

CANDIDATE'S ANSWER:
{answer}
---

## YOUR TASK — Relevance Score (0-10)

Evaluate on TWO dimensions, then combine:

### Dimension 1 — Directness (does the answer address the question?)
  10   Directly and fully answers what was asked, nothing missing.
  8-9  Mostly on target; minor tangent or one aspect left uncovered.
  6-7  Partially on target; answers some of the question but drifts or omits a key part.
  4-5  Tangential; only loosely related, major parts of the question unanswered.
  0-3  Off-topic or no meaningful attempt to answer the question.

### Dimension 2 — Depth & Evidence (does the answer go beyond surface-level?)
  10   Rich with specific examples, measurable results, or STAR-style narrative.
  8-9  Solid depth; one concrete example or some specificity.
  6-7  Some depth; general points with occasional detail.
  4-5  Surface-level only; generic statements, no concrete evidence.
  0-3  Near-empty, circular, or purely hypothetical.

### Final Score = round((Directness + Depth) / 2, 1)

## REASONING (one concise sentence, max 20 words)
State: what was answered well AND what was missing or generic.

Return ONLY valid JSON:
{{
  "directness_score": 7.0,
  "depth_score": 6.0,
  "score": 6.5,
  "reasoning": "Candidate answered the context but provided no concrete example or measurable outcome."
}}
"""

_RELEVANCE_WITH_RUBRIC_PROMPT = """You are a senior HR talent assessor scoring an interview answer
against a structured rubric.

---
QUESTION ASKED:
{question}

SCORING RUBRIC (defined by the recruiter):
{rubric}

CANDIDATE'S ANSWER:
{answer}
---

## YOUR TASK — Two-Dimensional Scoring

### Dimension 1 — Question Relevance (0-10)
Does the answer directly address what the question asks?
  10   Directly and fully answers what was asked.
  7-9  Mostly on target with minor gaps.
  5-6  Partially on target; misses a key aspect.
  3-4  Tangential; only loosely related.
  0-2  Off-topic or no meaningful attempt.

### Dimension 2 — Rubric Fit (0-10)
How well does the answer match the criteria in the rubric?
Score according to the rubric's own language and thresholds.
If the rubric specifies a band (e.g. "9-10: measurable outcome"), apply it strictly.

### Final Score = round((Relevance + Rubric_Fit) / 2, 1)
Clamp all scores to [0, 10].

## REASONING (one sentence, max 20 words)
Mention what rubric criteria were met and what was missing.

Return ONLY valid JSON:
{{
  "relevance_score": 7.0,
  "rubric_fit_score": 5.0,
  "score": 6.0,
  "reasoning": "Good situational framing but no measurable result — rubric requires quantified outcome."
}}
"""


# ── Result class ───────────────────────────────────────────────────────────────

class RelevanceScore:
    """Relevance scoring result for one QA pair."""

    def __init__(
        self,
        score:            float = 0.0,
        reasoning:        str   = "",
        directness_score: float | None = None,
        depth_score:      float | None = None,
        rubric_fit_score: float | None = None,
        skipped:          bool  = False,
    ):
        self.score            = round(max(0.0, min(10.0, float(score))), 1)
        self.reasoning        = str(reasoning).strip()[:300]
        self.directness_score = round(max(0.0, min(10.0, float(directness_score))), 1) if directness_score is not None else None
        self.depth_score      = round(max(0.0, min(10.0, float(depth_score))), 1)      if depth_score      is not None else None
        self.rubric_fit_score = round(max(0.0, min(10.0, float(rubric_fit_score))), 1) if rubric_fit_score is not None else None
        self.skipped          = skipped  # True when answer was absent/placeholder


# ── Per-pair worker ────────────────────────────────────────────────────────────

def _is_usable(answer: str) -> bool:
    if not answer:
        return False
    if answer == settings.segment_no_answer_placeholder:
        return False
    return len(answer.split()) >= settings.text_min_answer_words


def _score_one(pair: QAPair) -> RelevanceScore:
    answer = (pair.answer or "").strip()
    answer_words = len(answer.split()) if answer else 0
    
    print(f"[Relevance] Processing Q: {pair.question[:50]}... | Answer: {answer[:60]}... | Words: {answer_words}")
    
    if not _is_usable(answer):
        if answer == settings.segment_no_answer_placeholder:
            print(f"[Relevance] SKIPPED: No answer was extracted from the transcript.")
            return RelevanceScore(score=0.0, reasoning="No answer was extracted from the transcript.", skipped=True)
        print(f"[Relevance] SKIPPED: answer too short ({answer_words} words, min: {settings.text_min_answer_words})")
        return RelevanceScore(score=0.0, reasoning="Answer too short for reliable scoring.", skipped=True)

    rubric = (pair.rubric or "").strip()
    print(f"[Relevance] ✓ Calling LLM for evaluation...")

    try:
        if rubric:
            data = generate_json(
                _RELEVANCE_WITH_RUBRIC_PROMPT.format(
                    question=pair.question.strip(),
                    rubric=rubric,
                    answer=answer[:2500],
                )
            )
            result = RelevanceScore(
                score=           float(data.get("score",           5.0)),
                reasoning=       str(data.get("reasoning",        "")),
                directness_score=float(data.get("relevance_score", 5.0)),
                rubric_fit_score=float(data.get("rubric_fit_score",5.0)),
            )
            print(f"[Relevance] ✓ LLM returned: score={result.score}")
            return result
        else:
            data = generate_json(
                _RELEVANCE_PROMPT.format(
                    question=pair.question.strip(),
                    answer=answer[:2500],
                )
            )
            result = RelevanceScore(
                score=           float(data.get("score",           5.0)),
                reasoning=       str(data.get("reasoning",        "")),
                directness_score=float(data.get("directness_score",5.0)),
                depth_score=     float(data.get("depth_score",     5.0)),
            )
            print(f"[Relevance] ✓ LLM returned: score={result.score}")
            return result
    except Exception as e:
        print(f"[Relevance] ❌ LLM ERROR: {e}")
        return RelevanceScore(score=0.0, reasoning="Scoring error.")


# ── Public API ─────────────────────────────────────────────────────────────────

def run(qa_pairs: list[QAPair]) -> dict:
    """Score relevance for all QA pairs in parallel.

    Returns:
        {
          "per_question": list[RelevanceScore],  # aligned 1-to-1 with qa_pairs
          "overall_score": float,                # mean of all scores
        }
    """
    if not qa_pairs:
        return {"per_question": [], "overall_score": 0.0}

    results: list[RelevanceScore | None] = [None] * len(qa_pairs)
    max_workers = min(len(qa_pairs), settings.text_relevance_max_workers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_score_one, p): i for i, p in enumerate(qa_pairs)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
                print(f"[Relevance] Q{idx+1}: score={results[idx].score}")
            except Exception as e:
                print(f"[Relevance] Q{idx+1} failed: {e}")
                results[idx] = RelevanceScore()

    filled  = [r if r is not None else RelevanceScore() for r in results]
    scored  = [r for r in filled if not r.skipped]
    overall = round(sum(r.score for r in scored) / len(scored), 2) if scored else 0.0

    return {"per_question": filled, "overall_score": overall}
