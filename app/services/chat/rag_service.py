from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import re
from fastapi import HTTPException
from app.ai.openai_brain import (
    OpenAIBrainError,
    answer_chat_with_memory,
    classify_brain_query,
    stream_chat_with_memory,
)
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.session_document_chunk_repository import SessionDocumentChunkRepository
from app.services.documents.document_chunking_service import generate_mock_embedding
from app.services.github_services.github_connector_service import GitHubConnectorService
from app.services.jira_services.jira_connector_service import JiraConnectorService
from app.core.logger import logger


def _is_github_query(query: str) -> bool:
    normalized = (query or "").lower()
    github_keywords = [
        "github",
        "repo",
        "repository",
        "pull request",
        "pr ",
        "commit",
        "branch",
        "codebase",
    ]
    return any(keyword in normalized for keyword in github_keywords)


def _is_jira_query(query: str) -> bool:
    normalized = (query or "").lower()
    if any(keyword in normalized for keyword in ["jira", "ticket", "issue", "story", "bug", "epic"]):
        return True
    return bool(re.search(r"\b[A-Z][A-Z0-9]+-\d+\b", query or ""))


async def _classify_query_sources(query: str) -> dict:
    route = {
        "source_hint": None,
        "intent": "simple_lookup",
        "entities": [],
        "keywords": [],
        "needs_story_graph": False,
        "routing_mode": "deterministic",
    }

    exact_jira = bool(re.search(r"\b[A-Z][A-Z0-9]+-\d+\b", query or ""))
    deterministic_github = _is_github_query(query)
    deterministic_jira = _is_jira_query(query)

    if exact_jira:
        route["source_hint"] = "jira"
        route["routing_mode"] = "deterministic_exact_id"
        return route

    try:
        llm_route = await classify_brain_query(query)
        if isinstance(llm_route, dict):
            route.update(
                {
                    "source_hint": llm_route.get("source_hint"),
                    "intent": llm_route.get("intent") or route["intent"],
                    "entities": llm_route.get("entities") or [],
                    "keywords": llm_route.get("keywords") or [],
                    "needs_story_graph": bool(llm_route.get("needs_story_graph")),
                    "routing_mode": "llm",
                }
            )
    except OpenAIBrainError as exc:
        logger.warning("[RAG] LLM query routing failed for query=%s error=%s", query, exc)

    if route["source_hint"] not in {"jira", "github"}:
        if deterministic_jira:
            route["source_hint"] = "jira"
            route["routing_mode"] = "deterministic_fallback"
        elif deterministic_github:
            route["source_hint"] = "github"
            route["routing_mode"] = "deterministic_fallback"

    logger.info(
        "[RAG] Query routing decided source=%s mode=%s intent=%s query=%s",
        route["source_hint"],
        route["routing_mode"],
        route["intent"],
        query,
    )
    return route

async def retrieve_context_for_query(session_id: int, user_id: int, query: str, db: AsyncSession) -> str:
    query_emb = await generate_mock_embedding(query)
    
    global_repo = DocumentChunkRepository(db)
    global_chunks = await global_repo.search_by_embedding_for_owner(user_id, query_emb, limit=3)
    
    session_repo = SessionDocumentChunkRepository(db)
    session_chunks = await session_repo.search_by_embedding_for_session(session_id, query_emb, limit=3)
    
    context_texts = [c.chunk_text for c in global_chunks] + [c.chunk_text for c in session_chunks]
    routing = await _classify_query_sources(query)

    if routing["source_hint"] == "github":
        try:
            github_context = await GitHubConnectorService(db).get_context_for_query(user_id, query)
            if github_context:
                context_texts.append(github_context)
        except HTTPException as exc:
            context_texts.append(f"GitHub connector error: {exc.detail}")
        except Exception:
            context_texts.append("GitHub connector error: failed to fetch live GitHub context.")

    if routing["source_hint"] == "jira":
        try:
            jira_context = await JiraConnectorService(db).get_context_for_query(user_id, query)
            if jira_context:
                context_texts.append(jira_context)
        except HTTPException as exc:
            logger.warning("[RAG] Jira connector HTTP error for query=%s detail=%s", query, exc.detail)
            context_texts.append(f"Jira connector error: {exc.detail}")
        except Exception as exc:
            logger.exception("[RAG] Jira connector unexpected error for query=%s", query)
            context_texts.append(f"Jira connector error: failed to fetch live Jira context. Internal error: {exc}")
    
    if not context_texts:
        return ""
    
    return "\n\n---\n\n".join(context_texts)


async def retrieve_recent_history(session_id: int, user_id: int, db: AsyncSession, limit: int = 8) -> list[dict]:
    message_repo = ChatMessageRepository(db)
    messages = await message_repo.list_recent_by_session_and_user(session_id, user_id, limit=limit)

    return [
        {
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }
        for message in messages
    ]


async def prepare_rag_context(session_id: int, user_id: int, query: str, db: AsyncSession) -> dict:
    query_emb = await generate_mock_embedding(query)

    global_repo = DocumentChunkRepository(db)
    global_chunks = await global_repo.search_by_embedding_for_owner(user_id, query_emb, limit=3)

    session_repo = SessionDocumentChunkRepository(db)
    session_chunks = await session_repo.search_by_embedding_for_session(session_id, query_emb, limit=3)

    context_texts = [c.chunk_text for c in global_chunks] + [c.chunk_text for c in session_chunks]
    kb_sources = []
    routing = await _classify_query_sources(query)

    if global_chunks:
        kb_sources.append("global_documents")
    if session_chunks:
        kb_sources.append("session_documents")

    if routing["source_hint"] == "github":
        try:
            github_context = await GitHubConnectorService(db).get_context_for_query(user_id, query)
            if github_context:
                context_texts.append(github_context)
                kb_sources.append("github")
        except HTTPException as exc:
            context_texts.append(f"GitHub connector error: {exc.detail}")
        except Exception:
            context_texts.append("GitHub connector error: failed to fetch live GitHub context.")

    if routing["source_hint"] == "jira":
        try:
            jira_context = await JiraConnectorService(db).get_context_for_query(user_id, query)
            if jira_context:
                context_texts.append(jira_context)
                kb_sources.append("jira")
        except HTTPException as exc:
            logger.warning("[RAG] Jira connector HTTP error for query=%s detail=%s", query, exc.detail)
            context_texts.append(f"Jira connector error: {exc.detail}")
        except Exception as exc:
            logger.exception("[RAG] Jira connector unexpected error for query=%s", query)
            context_texts.append(f"Jira connector error: failed to fetch live Jira context. Internal error: {exc}")

    history = await retrieve_recent_history(session_id, user_id, db)
    context = "\n\n---\n\n".join(context_texts) if context_texts else ""

    return {
        "context": context,
        "history": history,
        "used_global_documents": bool(global_chunks),
        "used_session_documents": bool(session_chunks),
        "kb_sources": kb_sources,
        "is_kb_grounded": bool(context_texts),
        "routing": routing,
    }

async def generate_rag_answer(session_id: int, user_id: int, query: str, db: AsyncSession) -> str:
    prepared = await prepare_rag_context(session_id, user_id, query, db)
    context = prepared["context"]
    history = prepared["history"]

    if not context:
        if history:
            try:
                return await answer_chat_with_memory(
                    query=query,
                    conversation_history=history,
                    context="",
                )
            except OpenAIBrainError:
                return (
                    f"I remember our recent conversation, but I don't have enough document context "
                    f"to confidently answer: '{query}'"
                )

        return f"I don't have enough context in your documents to answer: '{query}'"

    try:
        return await answer_chat_with_memory(
            query=query,
            conversation_history=history,
            context=context,
        )
    except OpenAIBrainError:
        history_hint = ""
        if history:
            last_user_turns = [msg["content"] for msg in history if msg["role"] == "user"][-2:]
            if last_user_turns:
                history_hint = f"\n\nRecent conversation considered:\n- " + "\n- ".join(last_user_turns)

        return (
            f"Based on the documents, here is the simulated RAG answer to '{query}'."
            f"{history_hint}\n\nContext used:\n{context[:400]}..."
        )


async def generate_rag_answer_with_metadata(session_id: int, user_id: int, query: str, db: AsyncSession) -> dict:
    prepared = await prepare_rag_context(session_id, user_id, query, db)
    answer = await generate_rag_answer(session_id, user_id, query, db)
    return {
        "answer": answer,
        "used_global_documents": prepared["used_global_documents"],
        "used_session_documents": prepared["used_session_documents"],
        "source_chunks": [{"source": source} for source in prepared["kb_sources"]],
        "grounding_source": "kb" if prepared["is_kb_grounded"] else "model",
        "model_name": "rag-kb" if prepared["is_kb_grounded"] else "rag-model",
    }


async def stream_rag_answer(session_id: int, user_id: int, query: str, db: AsyncSession, prepared_context: dict | None = None):
    prepared = prepared_context or await prepare_rag_context(session_id, user_id, query, db)
    context = prepared["context"]
    history = prepared["history"]

    if not context and not history:
        fallback = f"I don't have enough context in your documents to answer: '{query}'"
        for chunk in _chunk_text_for_stream(fallback):
            yield chunk
        return

    try:
        async for chunk in stream_chat_with_memory(
            query=query,
            conversation_history=history,
            context=context,
        ):
            yield chunk
    except OpenAIBrainError:
        if not context:
            fallback = (
                f"I remember our recent conversation, but I don't have enough document context "
                f"to confidently answer: '{query}'"
            )
        else:
            fallback = (
                f"Based on the documents, here is the simulated RAG answer to '{query}'.\n\n"
                f"Context used:\n{context[:400]}..."
            )
        for chunk in _chunk_text_for_stream(fallback):
            yield chunk


def _chunk_text_for_stream(text: str, chunk_size: int = 40) -> list[str]:
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
