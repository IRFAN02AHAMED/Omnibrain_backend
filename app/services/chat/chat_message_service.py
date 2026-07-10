from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_session_repository import ChatSessionRepository
from app.models.chat_message import ChatMessage

async def add_message_to_session(session_id: int, user_id: int, role: str, content: str, db: AsyncSession, **kwargs) -> ChatMessage:
    session_repo = ChatSessionRepository(db)
    session = await session_repo.get_by_id_and_user(session_id, user_id)
    if not session:
        raise ValueError("Session not found")
        
    msg_repo = ChatMessageRepository(db)
    msg = await msg_repo.create_message(session_id, user_id, role, content, **kwargs)
    
    await session_repo.update_last_message(session)
    return msg

async def list_session_messages(session_id: int, user_id: int, db: AsyncSession) -> List[ChatMessage]:
    repo = ChatMessageRepository(db)
    return await repo.list_by_session_and_user(session_id, user_id)
