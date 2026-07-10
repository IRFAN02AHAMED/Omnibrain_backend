from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class ChatSessionBase(BaseModel):
    title: str
    is_pinned: bool = False
    is_archived: bool = False

class ChatSessionCreate(ChatSessionBase):
    user_id: int

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None
    last_message_at: Optional[datetime] = None
    message_count: Optional[int] = None

class ChatSessionResponse(ChatSessionBase):
    id: int
    user_id: int
    last_message_at: Optional[datetime]
    message_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
