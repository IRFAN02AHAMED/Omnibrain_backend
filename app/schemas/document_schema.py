from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class DocumentBase(BaseModel):
    file_name: str
    original_file_name: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    drive_file_id: Optional[str] = None
    drive_web_url: Optional[str] = None
    drive_folder_id: Optional[str] = None
    folder_path: Optional[str] = "OmniBrain AI/Global Documents"
    source_type: str
    processing_status: str = "pending"
    chunk_count: int = 0
    checksum: Optional[str] = None

class DocumentCreate(DocumentBase):
    owner_id: int

class DocumentUpdate(BaseModel):
    file_name: Optional[str] = None
    processing_status: Optional[str] = None
    chunk_count: Optional[int] = None
    checksum: Optional[str] = None
    synced_at: Optional[datetime] = None

class DocumentResponse(DocumentBase):
    id: int
    owner_id: int
    uploaded_at: Optional[datetime]
    synced_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
