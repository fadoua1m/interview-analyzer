# app/services/description_ai.py
"""AI enhancements for job descriptions and requirements."""
from app.services.mistral_client import generate


def enhance_description(title: str, company: str, description: str) -> str:
    prompt = f"""Rewrite this job description for a {title} at {company}.

Original:
{description[:800]}

Rules:
- 3 short paragraphs max
- Plain text only, no bullet points, no markdown
- Clear and professional
- Keep the original intent

Return only the rewritten description."""
    return generate(prompt)


def generate_requirements(title: str, company: str, description: str) -> str:
    prompt = f"""List requirements for a {title} at {company}.

Job context:
{description[:600]}

Rules:
- 6 to 8 items max
- Numbered list: 1. 2. 3. ...
- Each item one sentence, max 15 words
- Plain text only, no markdown

Return only the numbered list."""
    return generate(prompt)


def enhance_requirements(title: str, requirements: str) -> str:
    prompt = f"""Rewrite these job requirements for a {title} role.

Original:
{requirements[:600]}

Rules:
- Keep the same number of items
- Numbered list: 1. 2. 3. ...
- Each item one sentence, max 15 words
- Plain text only, no markdown

Return only the numbered list."""
    return generate(prompt)