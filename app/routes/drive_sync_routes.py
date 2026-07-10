from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.documents.drive_sync_service import sync_global_documents
from app.repositories.sync_log_repository import SyncLogRepository
from app.schemas.sync_log_schema import SyncLogResponse

router = APIRouter(prefix="/sync", tags=["Drive Sync"])

@router.post("/global", response_model=dict)
async def trigger_global_sync(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await sync_global_documents(current_user.id, db)

@router.get("/logs", response_model=List[SyncLogResponse])
async def get_sync_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = SyncLogRepository(db)
    return await repo.list_by_user(current_user.id)
