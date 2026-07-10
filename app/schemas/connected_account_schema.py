from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class ConnectedAccountBase(BaseModel):
    provider: str = "google"
    provider_account_id: str
    provider_email: Optional[str] = None
    provider_name: Optional[str] = None
    provider_picture: Optional[str] = None
    token_type: Optional[str] = None
    token_expires_at: Optional[int] = None
    scopes: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = None

class ConnectedAccountCreate(ConnectedAccountBase):
    user_id: int
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

class ConnectedAccountUpdate(BaseModel):
    provider_email: Optional[str] = None
    provider_name: Optional[str] = None
    provider_picture: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[int] = None
    scopes: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = None

class ConnectedAccountResponse(ConnectedAccountBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    # Never expose access_token or refresh_token in response

    model_config = ConfigDict(from_attributes=True)
