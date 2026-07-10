from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.documents.global_document_service import process_and_store_global_document
from app.repositories.document_repository import DocumentRepository
from app.schemas.document_schema import DocumentResponse

router = APIRouter(prefix="/documents", tags=["Global Documents"])

@router.post("/upload", response_model=DocumentResponse)
async def upload_global_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Uploads a global document, processes it, chunks it, and saves to Drive & DB."""
    return await process_and_store_global_document(current_user.id, file, db)

@router.get("/", response_model=List[DocumentResponse])
async def list_global_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all global documents for the user."""
    repo = DocumentRepository(db)
    return await repo.list_by_owner(current_user.id)
