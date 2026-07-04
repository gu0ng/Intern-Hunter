from typing import Any

from app.tools.llm_client import LLMClientError, deepseek_chat_json


def call_deepseek_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    """Central DeepSeek JSON tool used by Agent nodes."""
    return deepseek_chat_json(system_prompt=system_prompt, user_prompt=user_prompt)


__all__ = ["LLMClientError", "call_deepseek_json"]
