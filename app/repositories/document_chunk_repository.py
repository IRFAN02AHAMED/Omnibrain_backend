from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.document_chunk import DocumentChunk
from app.repositories.base_repository import BaseRepository

class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, DocumentChunk)

    async def bulk_create_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        return await self.bulk_create(chunks)

    async def get_by_document_id(self, document_id: int) -> List[DocumentChunk]:
        stmt = select(self.model).where(
            self.model.document_id == document_id,
            self.model.is_active == True
        ).order_by(self.model.chunk_index.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_document_id(self, document_id: int) -> None:
        stmt = delete(self.model).where(self.model.document_id == document_id)
        await self.db.execute(stmt)
        await self.db.commit()

    async def search_by_embedding_for_owner(self, owner_id: int, query_embedding: List[float], limit: int = 5) -> List[DocumentChunk]:
        stmt = select(self.model).where(
            self.model.owner_id == owner_id,
            self.model.is_active == True
        ).order_by(
            self.model.embedding.l2_distance(query_embedding)
        ).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
