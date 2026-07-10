from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.sync_log import SyncLog
from app.repositories.base_repository import BaseRepository
from datetime import datetime, timezone

class SyncLogRepository(BaseRepository[SyncLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, SyncLog)

    async def create_log(self, user_id: int, provider: str = "google_drive", sync_type: str = "manual_drive_sync", folder_path: str = "OmniBrain AI/Global Documents") -> SyncLog:
        log = SyncLog(
            user_id=user_id,
            provider=provider,
            sync_type=sync_type,
            folder_path=folder_path,
            status="started",
            started_at=datetime.now(timezone.utc)
        )
        return await self.create(log)

    async def update_result(self, log: SyncLog, status: str, result_counts: dict, error_message: Optional[str] = None) -> SyncLog:
        update_data = {
            "status": status,
            "completed_at": datetime.now(timezone.utc),
            "files_found": result_counts.get("files_found", 0),
            "files_added": result_counts.get("files_added", 0),
            "files_updated": result_counts.get("files_updated", 0),
            "files_skipped": result_counts.get("files_skipped", 0),
            "files_failed": result_counts.get("files_failed", 0),
            "error_message": error_message
        }
        return await self.update(log, update_data)

    async def list_by_user(self, user_id: int) -> List[SyncLog]:
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.is_active == True
        ).order_by(self.model.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
