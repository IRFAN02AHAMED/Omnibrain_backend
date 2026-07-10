from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.models.chat_session import ChatSession
from app.repositories.base_repository import BaseRepository

class ChatSessionRepository(BaseRepository[ChatSession]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ChatSession)

    async def create_session(self, user_id: int, title: str) -> ChatSession:
        session = ChatSession(user_id=user_id, title=title)
        return await self.create(session)

    async def list_by_user(self, user_id: int) -> List[ChatSession]:
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.is_active == True
        ).order_by(self.model.updated_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id_and_user(self, session_id: int, user_id: int) -> Optional[ChatSession]:
        stmt = select(self.model).where(
            self.model.id == session_id,
            self.model.user_id == user_id,
            self.model.is_active == True
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_last_message(self, session: ChatSession) -> ChatSession:
        return await self.update(session, {
            "last_message_at": datetime.now(timezone.utc),
            "message_count": session.message_count + 1
        })

    async def update_title(self, session: ChatSession, title: str) -> ChatSession:
        return await self.update(session, {"title": title})
