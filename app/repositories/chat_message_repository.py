from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.chat_message import ChatMessage
from app.repositories.base_repository import BaseRepository

class ChatMessageRepository(BaseRepository[ChatMessage]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ChatMessage)

    async def create_message(
        self, session_id: int, user_id: int, role: str, content: str,
        source_chunks: Optional[List[Dict[str, Any]]] = None,
        used_global_documents: bool = False,
        used_session_documents: bool = False,
        model_name: Optional[str] = None,
        token_count: Optional[int] = None
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            source_chunks=source_chunks,
            used_global_documents=used_global_documents,
            used_session_documents=used_session_documents,
            model_name=model_name,
            token_count=token_count
        )
        return await self.create(msg)

    async def list_by_session(self, session_id: int) -> List[ChatMessage]:
        stmt = select(self.model).where(
            self.model.session_id == session_id,
            self.model.is_active == True
        ).order_by(self.model.created_at.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_session_and_user(self, session_id: int, user_id: int) -> List[ChatMessage]:
        stmt = select(self.model).where(
            self.model.session_id == session_id,
            self.model.user_id == user_id,
            self.model.is_active == True
        ).order_by(self.model.created_at.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
