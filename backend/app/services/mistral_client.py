import random
import time
import json

from mistralai.client import Mistral
from app.config import settings


def _extract_text(response) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""

    message = getattr(choices[0], "message", None)
    if message is None:
        return ""

    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
            elif isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
                parts.append(str(item["text"]))
        return "\n".join(parts).strip()

    return ""


def generate(prompt: str) -> str:
    if not settings.mistral_api_key:
        raise RuntimeError("Missing MISTRAL_API_KEY in environment")

    max_retries = settings.mistral_max_retries
    base_delay = settings.mistral_retry_base_delay_sec
    client = Mistral(api_key=settings.mistral_api_key)

    for attempt in range(max_retries):
        try:
            response = client.chat.complete(
                model=settings.mistral_model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=settings.mistral_temperature,
            )

            text = _extract_text(response)
            if text:
                return text

            raise RuntimeError("Mistral returned an empty response")

        except Exception:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0.0, 0.2)
            time.sleep(delay)

    raise RuntimeError("Mistral generation failed after retries")


def generate_json(prompt: str) -> dict:
    if not settings.mistral_api_key:
        raise RuntimeError("Missing MISTRAL_API_KEY in environment")

    max_retries = settings.mistral_max_retries
    base_delay = settings.mistral_retry_base_delay_sec
    client = Mistral(api_key=settings.mistral_api_key)

    for attempt in range(max_retries):
        try:
            response = client.chat.complete(
                model=settings.mistral_model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            text = _extract_text(response)
            if not text:
                raise RuntimeError("Mistral returned an empty JSON response")

            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise RuntimeError("Mistral JSON response is not an object")
            return parsed

        except Exception:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0.0, 0.2)
            time.sleep(delay)

    raise RuntimeError("Mistral JSON generation failed after retries")
