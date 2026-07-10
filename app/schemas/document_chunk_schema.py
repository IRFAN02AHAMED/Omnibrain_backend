from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class DocumentChunkBase(BaseModel):
    chunk_index: int
    chunk_text: str
    token_count: Optional[int] = None
    page_number: Optional[int] = None
    metadata_: Optional[Dict[str, Any]] = None

class DocumentChunkCreate(DocumentChunkBase):
    document_id: int
    owner_id: int
    embedding: Optional[List[float]] = None

class DocumentChunkUpdate(BaseModel):
    chunk_text: Optional[str] = None
    embedding: Optional[List[float]] = None

class DocumentChunkResponse(DocumentChunkBase):
    id: int
    document_id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
