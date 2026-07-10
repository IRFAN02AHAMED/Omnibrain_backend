import json

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.chat_session_schema import ChatSessionResponse, ChatSessionCreate
from app.schemas.chat_message_schema import ChatMessageResponse, ChatMessageCreate, ChatTurnCreate, ChatTurnResponse
from app.schemas.session_document_schema import SessionDocumentResponse
from app.services.chat.chat_session_service import create_chat_session, list_chat_sessions
from app.services.chat.chat_message_service import (
    add_message_to_session,
    create_session_and_chat,
    get_or_create_session_for_chat,
    list_session_messages,
)
from app.services.documents.session_document_service import process_and_store_session_document
from app.repositories.session_document_repository import SessionDocumentRepository
from app.repositories.chat_session_repository import ChatSessionRepository
from app.services.chat.rag_service import stream_rag_answer, prepare_rag_context

router = APIRouter(prefix="/chats", tags=["Chats"])

@router.post("/", response_model=ChatSessionResponse)
async def create_session(data: ChatSessionCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await create_chat_session(current_user.id, data.title, db)

@router.get("/", response_model=List[ChatSessionResponse])
async def get_sessions(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await list_chat_sessions(current_user.id, db)

@router.post("/{session_id}/messages", response_model=ChatMessageResponse)
async def add_message(session_id: int, data: ChatMessageCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await add_message_to_session(session_id, current_user.id, data.role, data.content, db)

@router.post("/send", response_model=ChatTurnResponse)
async def send_chat_turn(
    data: ChatTurnCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        session, user_message, assistant_message = await create_session_and_chat(
            user_id=current_user.id,
            content=data.content,
            db=db,
            session_id=data.session_id,
            title=data.title,
        )
        return {
            "session": session,
            "user_message": user_message,
            "assistant_message": assistant_message,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/send/stream")
async def stream_chat_turn(
    data: ChatTurnCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        session = await get_or_create_session_for_chat(
            user_id=current_user.id,
            content=data.content,
            db=db,
            session_id=data.session_id,
            title=data.title,
        )
        user_message = await add_message_to_session(session.id, current_user.id, "user", data.content, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    async def event_stream():
        prepared = await prepare_rag_context(session.id, current_user.id, data.content, db)

        session_payload = {
            "type": "session",
            "session": {
                "id": session.id,
                "title": session.title,
                "last_message_at": session.last_message_at.isoformat() if session.last_message_at else None,
                "message_count": session.message_count,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "created_at": session.created_at.isoformat() if session.created_at else None,
            },
            "user_message": {
                "id": user_message.id,
                "role": user_message.role,
                "content": user_message.content,
                "created_at": user_message.created_at.isoformat() if user_message.created_at else None,
            },
        }
        yield json.dumps(session_payload) + "\n"

        assistant_text_parts: list[str] = []
        async for chunk in stream_rag_answer(
            session.id,
            current_user.id,
            data.content,
            db,
            prepared_context=prepared,
        ):
            assistant_text_parts.append(chunk)
            yield json.dumps({"type": "delta", "content": chunk}) + "\n"

        final_text = "".join(assistant_text_parts).strip()
        assistant_message = await add_message_to_session(
            session.id,
            current_user.id,
            "assistant",
            final_text,
            db,
            model_name="rag-kb" if prepared["is_kb_grounded"] else "rag-model",
            source_chunks=[{"source": source} for source in prepared["kb_sources"]],
            used_global_documents=prepared["used_global_documents"],
            used_session_documents=prepared["used_session_documents"],
        )

        done_payload = {
            "type": "done",
            "assistant_message": {
                "id": assistant_message.id,
                "role": assistant_message.role,
                "content": assistant_message.content,
                "created_at": assistant_message.created_at.isoformat() if assistant_message.created_at else None,
                "model_name": assistant_message.model_name,
                "used_global_documents": assistant_message.used_global_documents,
                "used_session_documents": assistant_message.used_session_documents,
                "source_chunks": assistant_message.source_chunks,
            },
        }
        yield json.dumps(done_payload) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.post("/{session_id}/chat", response_model=ChatTurnResponse)
async def chat_with_rag(
    session_id: int,
    data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        session, user_message, assistant_message = await create_session_and_chat(
            user_id=current_user.id,
            content=data.content,
            db=db,
            session_id=session_id,
        )
        return {
            "session": session,
            "user_message": user_message,
            "assistant_message": assistant_message,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@router.get("/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(session_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await list_session_messages(session_id, current_user.id, db)

@router.post("/{session_id}/documents", response_model=SessionDocumentResponse)
async def upload_session_document(
    session_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return await process_and_store_session_document(session_id, current_user.id, file, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{session_id}/documents", response_model=List[SessionDocumentResponse])
async def get_session_documents(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session_repo = ChatSessionRepository(db)
    session = await session_repo.get_by_id_and_user(session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    repo = SessionDocumentRepository(db)
    return await repo.list_by_session(session_id)
