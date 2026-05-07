# app/services/interview_ai.py
"""AI generation and enhancement for interview questions."""
from app.services.mistral_client import generate

_TYPE_CONTEXT = {
    "behavioral": "behavioral questions about past experiences, teamwork, conflict, and leadership.",
    "technical":  "technical questions on hard skills, problem-solving, coding, and system design.",
    "hr":         "HR questions on culture fit, motivation, career goals, and work style.",
    "mixed":      "a balanced mix of behavioral, technical, and HR questions.",
}

_SENIORITY_DEPTH = {
    "junior": "Keep questions simple. Focus on fundamentals and learning mindset. No system design.",
    "mid":    "Moderate depth. Focus on independent work, practical experience, and ownership.",
    "senior": "High depth. Expect system design, trade-offs, cross-team impact, and mentoring.",
    "lead":   "Strategic depth. Expect architectural decisions, team leadership, and stakeholder management.",
}


def generate_questions(
    title: str,
    company: str,
    interview_type: str,
    seniority_level: str,
    description: str,
    requirements: str,
    count: int = 10,
    language: str = "en",
) -> list[str]:
    type_context     = _TYPE_CONTEXT.get(interview_type, "general interview questions.")
    seniority_depth  = _SENIORITY_DEPTH.get(seniority_level, "")

    prompt = f"""Generate {count} interview questions for a {seniority_level} {title} at {company}.

Type: {type_context}
Seniority note: {seniority_depth}

Job context:
{description[:600]}

Requirements:
{requirements[:400]}

Rules:
- Each question must be one sentence, max 20 words
- Direct and specific — no preamble, no sub-questions
- Numbered list: 1. 2. 3. ...
- Plain text only
- Output language: {language}

Return only the numbered list."""

    return _parse_numbered_list(generate(prompt))


def enhance_question(
    title: str,
    interview_type: str,
    seniority_level: str,
    question: str,
    language: str = "en",
) -> str:
    prompt = f"""Rewrite this interview question for a {seniority_level} {title} ({interview_type} interview).

Original: {question}

Rules:
- One sentence, max 20 words
- Direct, specific, open-ended
- No preamble
- Output language: {language}

Return only the rewritten question."""

    return generate(prompt)


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_numbered_list(text: str) -> list[str]:
    result = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line[0].isdigit():
            dot = line.find(".")
            par = line.find(")")
            idx = min(
                dot if dot != -1 else 9999,
                par if par != -1 else 9999,
            )
            if idx < 4:
                line = line[idx + 1:].strip()
        if line:
            result.append(line)
    return result

def generate_rubric(
    question:        str,
    interview_type:  str,
    seniority_level: str,
    title:           str,
    language:        str = "en",
) -> str:
    prompt = f"""You are an expert HR evaluator. Create a scoring rubric for this interview question.

Question: {question}
Role: {seniority_level} {title} ({interview_type} interview)

Rules:
- 4 bands: 0-2, 3-5, 6-8, 9-10
- Each band is one sentence describing what that answer looks like
- Be specific to the question — no generic language
- Plain text only, no JSON, no markdown
- Output language: {language}

Format exactly like this:
0-2: <what a poor answer looks like>
3-5: <what a basic answer looks like>
6-8: <what a good answer looks like>
9-10: <what an excellent answer looks like>

Return only the 4 lines."""
    return generate(prompt).strip()


def enhance_rubric(
    question:        str,
    rubric:          str,
    interview_type:  str,
    seniority_level: str,
    title:           str,
    language:        str = "en",
) -> str:
    prompt = f"""You are an expert HR evaluator. Improve this scoring rubric for the interview question.

Question: {question}
Role: {seniority_level} {title} ({interview_type} interview)

Current rubric:
{rubric}

Rules:
- Keep the same 4-band format: 0-2, 3-5, 6-8, 9-10
- Make each band more specific and actionable
- Ensure bands clearly differentiate answer quality
- Plain text only
- Output language: {language}

Return only the 4 lines in the same format."""
    return generate(prompt).strip()