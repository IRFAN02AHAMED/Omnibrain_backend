from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.session_document_chunk import SessionDocumentChunk
from app.repositories.base_repository import BaseRepository

class SessionDocumentChunkRepository(BaseRepository[SessionDocumentChunk]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, SessionDocumentChunk)

    async def bulk_create_chunks(self, chunks: List[SessionDocumentChunk]) -> List[SessionDocumentChunk]:
        return await self.bulk_create(chunks)

    async def search_by_embedding_for_session(self, session_id: int, query_embedding: List[float], limit: int = 5) -> List[SessionDocumentChunk]:
        stmt = select(self.model).where(
            self.model.session_id == session_id,
            self.model.is_active == True
        ).order_by(
            self.model.embedding.l2_distance(query_embedding)
        ).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
