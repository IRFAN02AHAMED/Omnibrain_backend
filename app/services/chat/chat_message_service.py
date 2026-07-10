from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_session_repository import ChatSessionRepository
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.services.chat.chat_session_service import build_chat_title_from_message, create_chat_session
from app.services.chat.rag_service import generate_rag_answer

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


async def create_session_and_chat(
    user_id: int,
    content: str,
    db: AsyncSession,
    session_id: int | None = None,
    title: str | None = None,
) -> tuple[ChatSession, ChatMessage, ChatMessage]:
    session_repo = ChatSessionRepository(db)

    if session_id is not None:
        session = await session_repo.get_by_id_and_user(session_id, user_id)
        if not session:
            raise ValueError("Session not found")
    else:
        session = await create_chat_session(
            user_id=user_id,
            title=title or build_chat_title_from_message(content),
            db=db,
        )

    user_message = await add_message_to_session(session.id, user_id, "user", content, db)
    answer_text = await generate_rag_answer(session.id, user_id, content, db)
    assistant_message = await add_message_to_session(
        session.id,
        user_id,
        "assistant",
        answer_text,
        db,
        model_name="rag-mock",
    )

    return session, user_message, assistant_message
