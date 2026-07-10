from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class ChatMessageBase(BaseModel):
    role: str
    content: str
    source_chunks: Optional[List[Dict[str, Any]]] = None
    used_global_documents: bool = False
    used_session_documents: bool = False
    model_name: Optional[str] = None
    token_count: Optional[int] = None

class ChatMessageCreate(ChatMessageBase):
    pass


class ChatTurnCreate(BaseModel):
    content: str
    session_id: Optional[int] = None
    title: Optional[str] = None


class ChatTurnResponse(BaseModel):
    session: "ChatSessionResponse"
    user_message: "ChatMessageResponse"
    assistant_message: "ChatMessageResponse"

class ChatMessageUpdate(BaseModel):
    pass # Messages shouldn't be updated

class ChatMessageResponse(ChatMessageBase):
    id: int
    session_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


from app.schemas.chat_session_schema import ChatSessionResponse

ChatTurnResponse.model_rebuild()
