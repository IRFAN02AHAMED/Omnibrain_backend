import time
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from app.core.google_config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN_URL
from app.repositories.connected_account_repository import ConnectedAccountRepository
from app.models.connected_account import ConnectedAccount

async def get_user_google_account(user_id: int, db: AsyncSession) -> Optional[ConnectedAccount]:
    repo = ConnectedAccountRepository(db)
    return await repo.get_google_account_for_user(user_id)

async def refresh_if_expired(account: ConnectedAccount, db: AsyncSession, creds: Credentials) -> None:
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        repo = ConnectedAccountRepository(db)
        # Token expiration typically gives an absolute expiry time in creds.expiry (datetime)
        # Or we can just calculate now + expiration seconds
        expires_at = int(time.time()) + 3600
        if creds.expiry:
            expires_at = int(creds.expiry.timestamp())
        
        await repo.update_tokens(account, creds.token, expires_at)

async def get_user_google_credentials(user_id: int, db: AsyncSession) -> Credentials:
    account = await get_user_google_account(user_id, db)
    if not account or not account.access_token:
        raise ValueError("Google account not found or access token missing")

    creds = Credentials(
        token=account.access_token,
        refresh_token=account.refresh_token,
        token_uri=GOOGLE_TOKEN_URL,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=account.scopes.split(",") if account.scopes else []
    )

    await refresh_if_expired(account, db, creds)
    return creds

async def save_google_tokens(user_id: int, token_data: dict, user_info: dict, db: AsyncSession) -> ConnectedAccount:
    repo = ConnectedAccountRepository(db)
    return await repo.upsert_google_account(
        user_id=user_id,
        provider_account_id=user_info.get("id") or user_info.get("sub", ""),
        email=user_info.get("email", ""),
        name=user_info.get("name", ""),
        picture=user_info.get("picture", ""),
        token_data=token_data
    )
