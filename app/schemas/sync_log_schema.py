from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class SyncLogBase(BaseModel):
    provider: str = "google_drive"
    sync_type: str = "manual_drive_sync"
    folder_path: Optional[str] = "OmniBrain AI/Global Documents"
    status: str
    files_found: int = 0
    files_added: int = 0
    files_updated: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class SyncLogCreate(SyncLogBase):
    user_id: int

class SyncLogUpdate(BaseModel):
    status: Optional[str] = None
    files_found: Optional[int] = None
    files_added: Optional[int] = None
    files_updated: Optional[int] = None
    files_skipped: Optional[int] = None
    files_failed: Optional[int] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None

class SyncLogResponse(SyncLogBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
