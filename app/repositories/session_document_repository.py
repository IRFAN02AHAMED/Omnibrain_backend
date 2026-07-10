from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.session_document import SessionDocument
from app.repositories.base_repository import BaseRepository

class SessionDocumentRepository(BaseRepository[SessionDocument]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, SessionDocument)

    async def create_session_document(self, doc_data: dict) -> SessionDocument:
        doc = SessionDocument(**doc_data)
        return await self.create(doc)

    async def list_by_session(self, session_id: int) -> List[SessionDocument]:
        stmt = select(self.model).where(
            self.model.session_id == session_id,
            self.model.is_active == True
        ).order_by(self.model.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_session_and_owner(self, session_id: int, owner_id: int, doc_id: int) -> Optional[SessionDocument]:
        stmt = select(self.model).where(
            self.model.id == doc_id,
            self.model.session_id == session_id,
            self.model.owner_id == owner_id,
            self.model.is_active == True
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def verify_ownership(self, session_id: int, owner_id: int) -> bool:
        stmt = select(self.model).where(
            self.model.session_id == session_id,
            self.model.owner_id == owner_id,
            self.model.is_active == True
        ).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
