import json
from typing import Any

import httpx

from app.ai.prompts.brain_prompts import (
    CHAT_MEMORY_SYSTEM_PROMPT,
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


async def answer_chat_with_memory(
    query: str,
    conversation_history: list[dict[str, Any]],
    context: str,
) -> str:
    user_prompt = (
        f"Current user question:\n{query}\n\n"
        f"Recent conversation history:\n{json.dumps(conversation_history, ensure_ascii=True)}\n\n"
        f"Retrieved grounded context (this may include live connector data from Jira, GitHub, Google Drive, and stored KB chunks):\n"
        f"{context or 'No matching document context found.'}\n"
    )
    return await _chat_text(CHAT_MEMORY_SYSTEM_PROMPT, user_prompt)


async def stream_chat_with_memory(
    query: str,
    conversation_history: list[dict[str, Any]],
    context: str,
):
    user_prompt = (
        f"Current user question:\n{query}\n\n"
        f"Recent conversation history:\n{json.dumps(conversation_history, ensure_ascii=True)}\n\n"
        f"Retrieved grounded context (this may include live connector data from Jira, GitHub, Google Drive, and stored KB chunks):\n"
        f"{context or 'No matching document context found.'}\n"
    )

    if not has_openai_brain_config():
        raise OpenAIBrainError("OpenAI API key or model is not configured.")

    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": CHAT_MEMORY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "stream": True,
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=settings.OPENAI_TIMEOUT_SECONDS) as client:
        logger.info("[OpenAIBrain] Streaming model=%s", settings.OPENAI_MODEL)
        async with client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        ) as response:
            if response.status_code >= 400:
                error_text = await response.aread()
                raise OpenAIBrainError(
                    f"OpenAI stream failed: {response.status_code} {error_text.decode(errors='replace')}"
                )

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    break

                try:
                    payload = json.loads(data)
                    delta = payload["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except Exception as exc:
                    raise OpenAIBrainError(
                        f"Unexpected OpenAI streaming response format: {data}"
                    ) from exc


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


async def _chat_text(system_prompt: str, user_prompt: str) -> str:
    if not has_openai_brain_config():
        raise OpenAIBrainError("OpenAI API key or model is not configured.")

    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=settings.OPENAI_TIMEOUT_SECONDS) as client:
        logger.info("[OpenAIBrain] Calling text model=%s", settings.OPENAI_MODEL)
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
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise OpenAIBrainError(
            f"Unexpected OpenAI response format: {data}"
        ) from exc
