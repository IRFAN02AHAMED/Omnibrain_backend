from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
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

async def generate_rag_answer(session_id: int, user_id: int, query: str, db: AsyncSession) -> str:
    context = await retrieve_context_for_query(session_id, user_id, query, db)
    
    if not context:
        return f"I don't have enough context in your documents to answer: '{query}'"
    
    return f"Based on the documents, here is the simulated RAG answer to '{query}'.\n\nContext used:\n{context[:200]}..."
