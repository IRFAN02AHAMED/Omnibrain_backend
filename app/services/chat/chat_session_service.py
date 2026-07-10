from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.repositories.chat_session_repository import ChatSessionRepository
from app.models.chat_session import ChatSession

async def create_chat_session(user_id: int, title: str, db: AsyncSession) -> ChatSession:
    repo = ChatSessionRepository(db)
    return await repo.create_session(user_id, title)

async def list_chat_sessions(user_id: int, db: AsyncSession) -> List[ChatSession]:
    repo = ChatSessionRepository(db)
    return await repo.list_by_user(user_id)

async def get_chat_session(session_id: int, user_id: int, db: AsyncSession) -> ChatSession:
    repo = ChatSessionRepository(db)
    session = await repo.get_by_id_and_user(session_id, user_id)
    if not session:
        raise ValueError("Chat session not found")
    return session
