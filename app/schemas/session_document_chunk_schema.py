from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class SessionDocumentChunkBase(BaseModel):
    chunk_index: int
    chunk_text: str
    token_count: Optional[int] = None
    page_number: Optional[int] = None
    metadata_: Optional[Dict[str, Any]] = None

class SessionDocumentChunkCreate(SessionDocumentChunkBase):
    session_document_id: int
    session_id: int
    owner_id: int
    embedding: Optional[List[float]] = None

class SessionDocumentChunkUpdate(BaseModel):
    pass

class SessionDocumentChunkResponse(SessionDocumentChunkBase):
    id: int
    session_document_id: int
    session_id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
