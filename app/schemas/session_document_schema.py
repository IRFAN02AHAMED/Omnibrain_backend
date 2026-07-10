from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class SessionDocumentBase(BaseModel):
    file_name: str
    original_file_name: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    drive_file_id: Optional[str] = None
    drive_web_url: Optional[str] = None
    drive_folder_id: Optional[str] = None
    folder_path: Optional[str] = "OmniBrain AI/Chat Documents"
    processing_status: str = "pending"
    chunk_count: int = 0

class SessionDocumentCreate(SessionDocumentBase):
    session_id: int
    owner_id: int

class SessionDocumentUpdate(BaseModel):
    processing_status: Optional[str] = None
    chunk_count: Optional[int] = None

class SessionDocumentResponse(SessionDocumentBase):
    id: int
    session_id: int
    owner_id: int
    uploaded_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
