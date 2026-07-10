# app/services/google/google_auth_service.py
# Purpose: Handle Google OAuth login, token exchange, token refresh, and disconnect.

import httpx
from urllib.parse import urlencode
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.google_config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_REDIRECT_URI_V2,
    GOOGLE_AUTH_URL,
    GOOGLE_TOKEN_URL,
    GOOGLE_USERINFO_URL,
    GOOGLE_SCOPES,
)

from app.services.google.google_token_store import (
    save_google_account,
    get_google_account,
    update_google_access_token,
    delete_google_account,
    get_safe_google_account,
)

from app.core.security import create_access_token
from app.repositories.user_repository import UserRepository
from app.repositories.connected_account_repository import ConnectedAccountRepository
from app.services.google.google_drive_service import ensure_omnibrain_folders
from app.core.logger import logger

# ============================================================
# OLD TESTING FLOW
# Uses in-memory token store and requires user_id.
# ============================================================

def build_google_login_url(user_id: int | None = None) -> str:
    """Build the Google OAuth authorization URL for old testing flow."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    if user_id is not None:
        params["state"] = str(user_id)
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    """Exchange Google authorization code for tokens using OLD callback URI."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to exchange code: {response.text}")
    return response.json()


async def fetch_google_user_info(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch user info")
    return response.json()


async def connect_google_account(user_id: int, code: str) -> dict:
    """Old testing Google OAuth connection flow."""
    token_data = await exchange_code_for_tokens(code)
    access_token = token_data.get("access_token")
    user_info = await fetch_google_user_info(access_token)
    save_google_account(
        user_id=user_id,
        google_email=user_info.get("email", ""),
        name=user_info.get("name", ""),
        picture=user_info.get("picture", ""),
        access_token=access_token,
        refresh_token=token_data.get("refresh_token", ""),
        expires_at=str(token_data.get("expires_in", 3600)),
        scopes=token_data.get("scope", ""),
    )
    return get_safe_google_account(user_id)


async def refresh_google_access_token(user_id: int) -> dict:
    account = get_google_account(user_id)
    refresh_token = account.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    data = response.json()
    update_google_access_token(user_id, data.get("access_token"), str(data.get("expires_in", 3600)))
    return get_safe_google_account(user_id)


def disconnect_google_account(user_id: int) -> dict:
    delete_google_account(user_id)
    return {"message": "Disconnected"}


def get_connected_google_account(user_id: int) -> dict:
    return get_safe_google_account(user_id)


# ============================================================
# PRODUCTION DB-BACKED OAUTH FLOW
# ============================================================

def build_google_login_url_v2() -> str:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI_V2,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": "v2",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens_v2(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI_V2,
                "grant_type": "authorization_code",
            },
        )
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Token exchange failed")
    return response.json()


async def connect_google_account_db(code: str, db: AsyncSession) -> dict:
    token_data = await exchange_code_for_tokens_v2(code)
    google_access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)
    scopes = token_data.get("scope", "")

    user_info = await fetch_google_user_info(google_access_token)
    google_account_id = user_info.get("id")
    google_email = user_info.get("email")
    name = user_info.get("name", "")
    picture = user_info.get("picture", "")

    if not google_email:
        raise HTTPException(status_code=400, detail="Google account did not return an email address.")

    user_repo = UserRepository(db)
    user = await user_repo.find_or_create_by_email(email=google_email, full_name=name, profile_picture=picture)

    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    account_repo = ConnectedAccountRepository(db)
    
    await account_repo.upsert_google_account(
        user_id=user.id,
        provider_account_id=google_account_id,
        provider_email=google_email,
        provider_name=name,
        provider_picture=picture,
        access_token=google_access_token,
        refresh_token=refresh_token if refresh_token else None,
        token_expires_at=token_expires_at,
        scopes=scopes,
    )

    try:
        await ensure_omnibrain_folders(user_id=user.id, db=db)
    except Exception as folder_exc:
        logger.exception(f"[GoogleAuth] Drive folder setup failed: {folder_exc}")
        raise

    # Step 6: Generate app JWT
    jwt_token = create_access_token(str(user.id))

    logger.info(f"[GoogleAuth] Production login successful for user: {user.id}")

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "profile_picture": user.profile_picture,
        },
    }