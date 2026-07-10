import json
from typing import Any

import httpx

from app.ai.prompts.brain_prompts import (
    ROUTE_SYSTEM_PROMPT,
    STORY_GRAPH_SYSTEM_PROMPT,
    SYNTHESIS_SYSTEM_PROMPT,
)
from app.core.config import settings
from app.core.logger import logger


class OpenAIBrainError(Exception):
    """Raised when an OpenAI brain call cannot be completed."""


def has_openai_brain_config() -> bool:
    return bool(settings.OPENAI_API_KEY and settings.OPENAI_MODEL)


async def classify_brain_query(query: str) -> dict[str, Any]:
    user_prompt = f"User query:\n{query}"
    return await _chat_json(ROUTE_SYSTEM_PROMPT, user_prompt)


async def build_story_graph_from_chunks(
    query: str,
    entities: list[str],
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    user_prompt = (
        f"User query:\n{query}\n\n"
        f"Anchor entities:\n{json.dumps(entities)}\n\n"
        f"Evidence chunks:\n{json.dumps(chunks, ensure_ascii=True)}"
    )
    return await _chat_json(STORY_GRAPH_SYSTEM_PROMPT, user_prompt)


async def synthesize_brain_answer(
    query: str,
    chunks: list[dict[str, Any]],
    story_graph: dict[str, Any] | None,
) -> dict[str, Any]:
    user_prompt = (
        f"User query:\n{query}\n\n"
        f"Story graph:\n{json.dumps(story_graph, ensure_ascii=True) if story_graph else 'null'}\n\n"
        f"Evidence chunks:\n{json.dumps(chunks, ensure_ascii=True)}"
    )
    return await _chat_json(SYNTHESIS_SYSTEM_PROMPT, user_prompt)


async def _chat_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    if not has_openai_brain_config():
        raise OpenAIBrainError("OpenAI API key or model is not configured.")

    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=settings.OPENAI_TIMEOUT_SECONDS) as client:
        logger.info("[OpenAIBrain] Calling model=%s", settings.OPENAI_MODEL)
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )

    if response.status_code >= 400:
        raise OpenAIBrainError(
            f"OpenAI call failed: {response.status_code} {response.text}"
        )

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        raise OpenAIBrainError(
            f"Unexpected OpenAI response format: {data}"
        ) from exc
