"""
Competency Detector
===================
Detects demonstrated soft skills / competencies in interview answers.

Per-answer analysis using the recruiter-defined competency bank.
Produces DetectedSkill objects with evidence quotes and strength ratings.

Strength levels:
  strong          — Measurable outcome clearly tied to candidate's action
  moderate        — Clear example without quantified result
  weak            — Mentioned but no concrete proof
  not_demonstrated— Target skill was expected but not evidenced (explicit gap)
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.config                  import settings
from app.schemas.analysis        import QAPair, DetectedSkill
from app.services.mistral_client import generate_json
from app.services.softskills_bank import get_competency_bank_for_language


# ── Prompt ─────────────────────────────────────────────────────────────────────

_DETECTION_PROMPT = """You are a senior HR assessor evaluating which competencies a candidate
demonstrates in a single interview answer.

---
INTERVIEW QUESTION:
{question}

TARGET COMPETENCIES TO EVALUATE (defined by the recruiter):
{target_skills_definitions}

CANDIDATE'S ANSWER:
{answer}
---

## YOUR TASK

### Part 1 — Target Competency Assessment
For EACH competency listed above, decide:

  Strength levels:
    "strong"           → Candidate gives a specific example WITH a measurable or verifiable outcome.
                         ("I reduced onboarding time by 30% by redesigning the process.")
    "moderate"         → Clear concrete example, but outcome is implied or not quantified.
                         ("I led the team through the migration and it went smoothly.")
    "weak"             → Skill is mentioned or hinted at, but no real example provided.
                         ("I believe in collaboration.")
    "not_demonstrated" → No evidence for this competency in the answer.

  Evidence rules:
    - `quote` must be a verbatim or near-verbatim excerpt from the answer (max 80 words).
    - If strength is "not_demonstrated", set quote to "" and reasoning to "No evidence found."
    - Do NOT invent quotes or fabricate evidence.

### Part 2 — Additional Competencies
Beyond the target list, identify up to 3 OTHER competencies clearly demonstrated in this answer.
Only include competencies from this allowed list (use exact keys):
{allowed_additional_keys}

Apply the same evidence standards. Do not repeat target competencies here.
If none are clearly demonstrated, return an empty list.

Return ONLY valid JSON (no markdown):
{{
  "target_skills": [
    {{
      "name": "communication",
      "strength": "moderate",
      "quote": "I presented the findings to the board and they approved the budget",
      "reasoning": "Clear presentation example but no impact metric provided."
    }}
  ],
  "additional_skills": [
    {{
      "name": "leadership",
      "strength": "strong",
      "quote": "I mentored two junior engineers who were promoted within a year",
      "reasoning": "Concrete mentoring with measurable career outcome."
    }}
  ]
}}
"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _normalize(name: str) -> str:
    return (name or "").strip().lower().replace("-", "_").replace(" ", "_")


def _build_target_definitions(target_skills: list[str], bank: dict[str, str]) -> str:
    lines = []
    for skill in target_skills:
        key = _normalize(skill)
        definition = bank.get(key, "")
        if definition:
            lines.append(f"  • {key}: {definition}")
        else:
            lines.append(f"  • {key}")
    return "\n".join(lines) if lines else "(none specified)"


def _allowed_additional_keys(bank: dict[str, str], exclude: set[str]) -> str:
    keys = sorted(k for k in bank if k not in exclude)
    return ", ".join(keys[:40])   # cap to keep prompt manageable


# ── Per-pair worker ────────────────────────────────────────────────────────────

def _detect_one(pair: QAPair, bank: dict[str, str]) -> list[DetectedSkill]:
    answer = (pair.answer or "").strip()
    if not answer or len(answer.split()) < settings.text_min_answer_words:
        return []

    target_skills = [_normalize(s) for s in (pair.target_skills or []) if s]
    valid_targets  = [s for s in target_skills if s in bank]

    if not valid_targets:
        return []

    target_defs    = _build_target_definitions(valid_targets, bank)
    additional_allowed = _allowed_additional_keys(bank, set(valid_targets))

    prompt = _DETECTION_PROMPT.format(
        question=pair.question.strip(),
        target_skills_definitions=target_defs,
        answer=answer[:2500],
        allowed_additional_keys=additional_allowed,
    )

    try:
        result = generate_json(prompt)
    except Exception as e:
        print(f"[Competency] LLM call failed for Q '{pair.question[:50]}': {e}")
        return []

    detected: list[DetectedSkill] = []

    # Target competencies (include not_demonstrated for gap reporting)
    for item in result.get("target_skills", []):
        if not isinstance(item, dict):
            continue
        name     = _normalize(item.get("name", ""))
        strength = str(item.get("strength", "")).strip().lower()
        if name not in bank:
            continue
        if strength not in {"strong", "moderate", "weak", "not_demonstrated"}:
            strength = "weak"
        detected.append(DetectedSkill(
            name=       name,
            strength=   strength,
            quote=      str(item.get("quote",     ""))[:300],
            description=str(item.get("reasoning", ""))[:200],
        ))

    # Additional competencies (only demonstrated ones)
    existing = {d.name for d in detected}
    for item in result.get("additional_skills", []):
        if not isinstance(item, dict):
            continue
        name     = _normalize(item.get("name", ""))
        strength = str(item.get("strength", "moderate")).strip().lower()
        if name not in bank or name in existing:
            continue
        if strength not in {"strong", "moderate", "weak"}:
            strength = "moderate"
        detected.append(DetectedSkill(
            name=       name,
            strength=   strength,
            quote=      str(item.get("quote",     ""))[:300],
            description=str(item.get("reasoning", ""))[:200],
        ))
        existing.add(name)

    return detected


# ── Deduplication / ranking ────────────────────────────────────────────────────

def _deduplicate(all_skills: list[DetectedSkill], max_skills: int = 10) -> list[DetectedSkill]:
    """Keep strongest evidence per skill name, return top N by strength."""
    _order = {"strong": 3, "moderate": 2, "weak": 1, "not_demonstrated": 0}
    by_name: dict[str, DetectedSkill] = {}

    for skill in all_skills:
        existing = by_name.get(skill.name)
        if not existing:
            by_name[skill.name] = skill
        else:
            # Prefer higher strength; on tie, prefer longer quote (more evidence)
            if _order.get(skill.strength, 0) > _order.get(existing.strength, 0):
                by_name[skill.name] = skill
            elif _order.get(skill.strength, 0) == _order.get(existing.strength, 0):
                if len(skill.quote) > len(existing.quote):
                    by_name[skill.name] = skill

    sorted_skills = sorted(
        by_name.values(),
        key=lambda s: (-_order.get(s.strength, 0), s.name),
    )
    return sorted_skills[:max_skills]


# ── Public API ─────────────────────────────────────────────────────────────────

def run(qa_pairs: list[QAPair], language: str = "en") -> list[DetectedSkill]:
    """Detect and deduplicate competencies across all QA pairs.

    Args:
        qa_pairs: interview Q&A pairs (must have target_skills set)
        language: "en" or "fr" — selects the right competency bank

    Returns:
        Deduplicated list of up to 10 DetectedSkill objects (strongest first).
    """
    if not qa_pairs:
        return []

    bank = get_competency_bank_for_language(language) or {}
    if not bank:
        print(f"[Competency] No competency bank found for language='{language}'")
        return []

    all_detected: list[DetectedSkill] = []
    max_workers = min(len(qa_pairs), settings.text_relevance_max_workers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_detect_one, p, bank): i
            for i, p in enumerate(qa_pairs)
            if p.target_skills
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                skills = future.result()
                all_detected.extend(skills)
                print(f"[Competency] Q{idx+1}: detected {len(skills)} skills")
            except Exception as e:
                print(f"[Competency] Q{idx+1} failed: {e}")

    final = _deduplicate(all_detected, max_skills=settings.softskills_max_skills)
    print(f"[Competency] Final: {len(final)} unique skills after deduplication")
    return final
