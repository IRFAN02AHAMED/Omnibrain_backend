# app/services/google/google_auth_service.py
# Purpose: Handle Google OAuth login, token exchange, token refresh, and disconnect.

import httpx
from urllib.parse import urlencode
from fastapi import HTTPException

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


# ─────────────────────────────────────────────────────────────────────────────
# OLD TESTING FLOW
# Uses in-memory token store and requires user_id.
# Routes:
#   GET /auth/google/login?user_id=1
#   GET /auth/google/callback
# ─────────────────────────────────────────────────────────────────────────────

def build_google_login_url(user_id: int | None = None) -> str:
    """
    Build the Google OAuth authorization URL for old testing flow.

    If user_id is provided, it is sent as OAuth state so the callback
    can know which temporary test user is connecting.
    """
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
    """
    Exchange Google authorization code for tokens using OLD callback URI.

    Used only by:
        /auth/google/callback
    """
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
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange authorization code for tokens: {response.text}",
        )

    return response.json()


async def fetch_google_user_info(access_token: str) -> dict:
    """
    Fetch authenticated Google user's profile.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch Google user info: {response.text}",
        )

    return response.json()


async def connect_google_account(user_id: int, code: str) -> dict:
    """
    Old testing Google OAuth connection flow.

    Saves Google tokens in temporary in-memory store.
    """
    token_data = await exchange_code_for_tokens(code)

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)
    scopes = token_data.get("scope", "")

    if not access_token:
        raise HTTPException(
            status_code=400,
            detail="Google did not return an access token.",
        )

    user_info = await fetch_google_user_info(access_token)

    google_email = user_info.get("email", "")
    name = user_info.get("name", "")
    picture = user_info.get("picture", "")

    save_google_account(
        user_id=user_id,
        google_email=google_email,
        name=name,
        picture=picture,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=str(expires_in),
        scopes=scopes,
    )

    return get_safe_google_account(user_id)


async def refresh_google_access_token(user_id: int) -> dict:
    """
    Refresh Google access token for old testing flow.
    """
    account = get_google_account(user_id)
    refresh_token = account.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=400,
            detail=(
                "No refresh token available. Please reconnect your Google account "
                f"via GET /auth/google/login?user_id={user_id}"
            ),
        )

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

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to refresh Google access token: {response.text}",
        )

    token_data = response.json()
    new_access_token = token_data.get("access_token")
    new_expires_in = token_data.get("expires_in", 3600)

    update_google_access_token(
        user_id=user_id,
        access_token=new_access_token,
        expires_at=str(new_expires_in),
    )

    return get_safe_google_account(user_id)


def disconnect_google_account(user_id: int) -> dict:
    """
    Disconnect Google account from old in-memory testing store.
    """
    delete_google_account(user_id)
    return {"message": f"Google account disconnected for user_id={user_id}."}


def get_connected_google_account(user_id: int) -> dict:
    """
    Get safe connected Google account info from old testing store.
    """
    return get_safe_google_account(user_id)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTION DB-BACKED OAUTH FLOW
# Uses connected_accounts table.
# Routes:
#   GET /auth/google/login/v2
#   GET /auth/google/callback/v2
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.repositories.user_repository import UserRepository
from app.repositories.connected_account_repository import ConnectedAccountRepository
from app.services.google.google_drive_service import ensure_omnibrain_folders
from app.core.logger import logger


def build_google_login_url_v2() -> str:
    """
    Build Google OAuth authorization URL for production DB-backed flow.

    Important:
    This MUST use GOOGLE_REDIRECT_URI_V2.
    If it uses GOOGLE_REDIRECT_URI, Google will return to old callback
    and you will get the user_id error.
    """
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
    """
    Exchange Google authorization code for tokens using V2 callback URI.

    Used only by:
        /auth/google/callback/v2

    Important:
    The redirect_uri here must exactly match the redirect_uri used in
    build_google_login_url_v2().
    """
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
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange authorization code for tokens: {response.text}",
        )

    return response.json()


async def connect_google_account_db(code: str, db: AsyncSession) -> dict:
    """
    Full production Google OAuth connection flow using database.

    Steps:
      1. Exchange authorization code for Google tokens.
      2. Fetch Google user profile.
      3. Find or create app user.
      4. Save Google account tokens in connected_accounts.
      5. Ensure OmniBrain AI Drive folders exist.
      6. Generate application JWT.
      7. Return JWT and safe user info.
    """

    # Step 1: Exchange code for Google tokens using V2 redirect URI
    token_data = await exchange_code_for_tokens_v2(code)

    google_access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)
    scopes = token_data.get("scope", "")

    if not google_access_token:
        raise HTTPException(
            status_code=400,
            detail="Google did not return an access token.",
        )

    # Step 2: Fetch Google profile
    user_info = await fetch_google_user_info(google_access_token)

    google_account_id = user_info.get("id")
    google_email = user_info.get("email", "")
    name = user_info.get("name", "")
    picture = user_info.get("picture", "")

    if not google_email:
        raise HTTPException(
            status_code=400,
            detail="Google account did not return an email address.",
        )

    # Step 3: Find or create app user
    # Step 3: Find or create app user
    user_repo = UserRepository(db)

    existing_user = await user_repo.get_by_email(google_email)

    if existing_user:
        user = existing_user

        if user.full_name != name or user.profile_picture != picture:
            await user_repo.update(
                user,
                {
                    "full_name": name,
                    "profile_picture": picture,
                },
            )

        logger.info(f"[GoogleAuth] Existing user found: id={user.id} email={google_email}")

    else:
        user = await user_repo.create_google_user(
            email=google_email,
            full_name=name,
            profile_picture=picture,
        )

    logger.info(f"[GoogleAuth] New user created: id={user.id} email={google_email}")
    # Step 4: Save/update Google connected account
    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    account_repo = ConnectedAccountRepository(db)

    await account_repo.upsert_google_account(
        user_id=user.id,
        provider_account_id=str(google_account_id) if google_account_id else None,
        provider_email=google_email,
        provider_name=name,
        provider_picture=picture,
        access_token=google_access_token,
        refresh_token=refresh_token if refresh_token else None,
        token_expires_at=token_expires_at,
        scopes=scopes,
    )

    # Step 5: Ensure Google Drive folders exist
    # If this fails, login should still succeed.
    try:
        await ensure_omnibrain_folders(user_id=user.id, db=db)
    except Exception as folder_exc:
        logger.warning(f"[GoogleAuth] Drive folder setup warning: {folder_exc}")

    # Step 6: Generate app JWT
    # This JWT is what the frontend stores as localStorage access_token.
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