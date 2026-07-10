from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.ai.openai_brain import OpenAIBrainError, answer_chat_with_memory, stream_chat_with_memory
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.session_document_chunk_repository import SessionDocumentChunkRepository
from app.services.documents.document_chunking_service import generate_mock_embedding

async def retrieve_context_for_query(session_id: int, user_id: int, query: str, db: AsyncSession) -> str:
    query_emb = await generate_mock_embedding(query)
    
    global_repo = DocumentChunkRepository(db)
    global_chunks = await global_repo.search_by_embedding_for_owner(user_id, query_emb, limit=3)
    
    session_repo = SessionDocumentChunkRepository(db)
    session_chunks = await session_repo.search_by_embedding_for_session(session_id, query_emb, limit=3)
    
    context_texts = [c.chunk_text for c in global_chunks] + [c.chunk_text for c in session_chunks]
    
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

async def generate_rag_answer(session_id: int, user_id: int, query: str, db: AsyncSession) -> str:
    context = await retrieve_context_for_query(session_id, user_id, query, db)
    history = await retrieve_recent_history(session_id, user_id, db)

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


async def stream_rag_answer(session_id: int, user_id: int, query: str, db: AsyncSession):
    context = await retrieve_context_for_query(session_id, user_id, query, db)
    history = await retrieve_recent_history(session_id, user_id, db)

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
