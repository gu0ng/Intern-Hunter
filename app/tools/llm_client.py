import json
from typing import Any

import requests

from app.config import settings


class LLMClientError(RuntimeError):
    pass


def parse_json_object(raw: str) -> dict[str, Any]:
    """Parse a model response into a JSON object with conservative cleanup."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMClientError(f"LLM output is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LLMClientError("LLM output JSON must be an object.")
    return parsed


def chat_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    return _chat_json(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def deepseek_chat_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    return _chat_json(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def _chat_json(api_key: str, base_url: str, model: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    if not api_key:
        raise LLMClientError("LLM API key is not configured.")

    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    return parse_json_object(content)
