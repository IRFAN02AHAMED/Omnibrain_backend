# app/services/google/google_client_service.py
# Purpose: Create reusable Google API clients for Drive, Docs, Sheets, and Gmail.
# Supports:
# 1. Old in-memory token_store flow
# 2. New DB-backed connected_accounts flow

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.google_config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_TOKEN_URL,
    GOOGLE_SCOPES,
)

from app.repositories.connected_account_repository import ConnectedAccountRepository


# ============================================================
# OLD TESTING FLOW CLIENTS
# These are used by old routes/services that pass account: dict
# Example:
#   get_drive_client(account)
#   get_docs_client(account)
# ============================================================

def create_google_credentials(account: dict) -> Credentials:
    """
    Create Google Credentials object from old in-memory google_token_store account dict.
    """
    scopes = account.get("scopes")

    if isinstance(scopes, str):
        # Google returns scopes as space-separated string.
        scopes = scopes.split(" ")

    if not scopes:
        scopes = GOOGLE_SCOPES

    return Credentials(
        token=account.get("access_token"),
        refresh_token=account.get("refresh_token"),
        token_uri=GOOGLE_TOKEN_URL,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=scopes,
    )


def get_drive_client(account: dict):
    """
    Old testing Drive client.
    Used by old route:
        GET /google/drive/files?user_id=1
    """
    credentials = create_google_credentials(account)
    return build("drive", "v3", credentials=credentials)


def get_docs_client(account: dict):
    """
    Old testing Google Docs client.
    Used by google_docs_service.py.
    """
    credentials = create_google_credentials(account)
    return build("docs", "v1", credentials=credentials)


def get_sheets_client(account: dict):
    """
    Old testing Google Sheets client.
    """
    credentials = create_google_credentials(account)
    return build("sheets", "v4", credentials=credentials)


def get_gmail_client(account: dict):
    """
    Old testing Gmail client.
    """
    credentials = create_google_credentials(account)
    return build("gmail", "v1", credentials=credentials)


# ============================================================
# DB-BACKED PRODUCTION CREDENTIALS
# These use connected_accounts table.
# ============================================================

async def get_user_google_credentials(
    user_id: int,
    db: AsyncSession,
) -> Credentials:
    """
    Get Google Credentials from connected_accounts table.
    Auto-refresh token if expired.
    """
    repo = ConnectedAccountRepository(db)

    account = await repo.get_by_user_id(user_id, provider="google")

    if not account or not account.access_token:
        raise HTTPException(
            status_code=404,
            detail="Google account not connected. Please login with Google first.",
        )

    scopes = account.scopes

    if isinstance(scopes, str):
        scopes = scopes.split(" ")

    if not scopes:
        scopes = GOOGLE_SCOPES

    credentials = Credentials(
        token=account.access_token,
        refresh_token=account.refresh_token,
        token_uri=GOOGLE_TOKEN_URL,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=scopes,
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

        await repo.update_tokens(
            account=account,
            access_token=credentials.token,
            expires_at=credentials.expiry,
        )

    return credentials


async def get_drive_client_for_user(
    user_id: int,
    db: AsyncSession,
):
    """
    Production DB-backed Google Drive client.
    Used by:
        GET /google/drive/files/me
        POST /google/drive/upload
        POST /sync/global
    """
    credentials = await get_user_google_credentials(user_id, db)
    return build("drive", "v3", credentials=credentials)


async def get_docs_client_for_user(
    user_id: int,
    db: AsyncSession,
):
    """
    Production DB-backed Google Docs client.
    """
    credentials = await get_user_google_credentials(user_id, db)
    return build("docs", "v1", credentials=credentials)


async def get_sheets_client_for_user(
    user_id: int,
    db: AsyncSession,
):
    """
    Production DB-backed Google Sheets client.
    """
    credentials = await get_user_google_credentials(user_id, db)
    return build("sheets", "v4", credentials=credentials)


async def get_gmail_client_for_user(
    user_id: int,
    db: AsyncSession,
):
    """
    Production DB-backed Gmail client.
    """
    credentials = await get_user_google_credentials(user_id, db)
    return build("gmail", "v1", credentials=credentials)