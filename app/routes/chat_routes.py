from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.chat_session_schema import ChatSessionResponse, ChatSessionCreate
from app.schemas.chat_message_schema import ChatMessageResponse, ChatMessageCreate
from app.schemas.session_document_schema import SessionDocumentResponse
from app.services.chat.chat_session_service import create_chat_session, list_chat_sessions
from app.services.chat.chat_message_service import add_message_to_session, list_session_messages
from app.services.documents.session_document_service import process_and_store_session_document
from app.services.chat.rag_service import generate_rag_answer
from app.repositories.session_document_repository import SessionDocumentRepository
from app.repositories.chat_session_repository import ChatSessionRepository
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

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

@router.post("/{session_id}/chat", response_model=ChatMessageResponse)
async def chat_with_rag(
    session_id: int, 
    data: ChatMessageCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    await add_message_to_session(session_id, current_user.id, "user", data.content, db)
    answer_text = await generate_rag_answer(session_id, current_user.id, data.content, db)
    return await add_message_to_session(session_id, current_user.id, "assistant", answer_text, db, model_name="rag-mock")

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

