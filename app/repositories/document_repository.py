from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document
from app.repositories.base_repository import BaseRepository

class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Document)

    async def create_document(self, doc_data: dict) -> Document:
        doc = Document(**doc_data)
        return await self.create(doc)

    async def list_by_owner(self, owner_id: int) -> List[Document]:
        stmt = select(self.model).where(
            self.model.owner_id == owner_id,
            self.model.is_active == True
        ).order_by(self.model.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_owner_and_id(self, owner_id: int, doc_id: int) -> Optional[Document]:
        stmt = select(self.model).where(
            self.model.id == doc_id,
            self.model.owner_id == owner_id,
            self.model.is_active == True
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_drive_file_id(self, owner_id: int, drive_file_id: str) -> Optional[Document]:
        stmt = select(self.model).where(
            self.model.owner_id == owner_id,
            self.model.drive_file_id == drive_file_id,
            self.model.is_active == True
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete_document(self, document: Document) -> Document:
        return await self.soft_delete(document)
