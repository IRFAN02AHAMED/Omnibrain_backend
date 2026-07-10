# app/services/google/google_auth_service.py
# Purpose: Handle Google OAuth login, token exchange, token refresh, and disconnect.
# pip install google-api-python-client google-auth google-auth-oauthlib python-dotenv

import httpx
from urllib.parse import urlencode
from fastapi import HTTPException

from app.core.google_config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
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


def build_google_login_url(user_id: int | None = None) -> str:
    """
    Build the Google OAuth authorization URL.

    The user will be redirected to this URL to log in with their Google account.
    Uses access_type=offline and prompt=consent to ensure a refresh_token is
    always returned during development.

    If user_id is provided, it is sent as the OAuth `state` parameter so the
    callback can identify which application user is connecting.

    Args:
        user_id: Optional application user ID to embed in the OAuth state.

    Returns:
        str: Full Google OAuth authorization URL with all query parameters.
    """
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",           # Required to get refresh_token
        "prompt": "consent",                # Force consent screen every time (ensures refresh_token)
        "include_granted_scopes": "true",   # Incremental authorization
    }

    # Pass user_id as state so the callback can identify the user
    if user_id is not None:
        params["state"] = str(user_id)

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange a Google authorization code for access and refresh tokens.

    Sends a POST request to GOOGLE_TOKEN_URL with the authorization code,
    client credentials, and redirect URI.

    Args:
        code: The authorization code received from Google OAuth callback.

    Returns:
        dict: Token response containing access_token, refresh_token, expires_in,
              token_type, and scope.

    Raises:
        HTTPException: If the token exchange fails (e.g., invalid code).
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
    Fetch the authenticated Google user's profile information.

    Uses the access token to call Google's UserInfo endpoint and retrieve
    the user's email, name, and profile picture.

    Args:
        access_token: A valid Google OAuth access token.

    Returns:
        dict: User profile with keys: id, email, name, picture, etc.

    Raises:
        HTTPException: If fetching user info fails (e.g., expired token).
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
    Full Google OAuth connection flow.

    Performs three steps:
      1. Exchanges the authorization code for access + refresh tokens.
      2. Fetches the Google user's profile (email, name, picture).
      3. Saves the connected account to temporary in-memory storage.

    Args:
        user_id: The application user ID to associate with this Google account.
        code: The authorization code from Google OAuth callback.

    Returns:
        dict: Safe account information (without tokens) for the API response.
    """
    # Step 1: Exchange authorization code for tokens
    token_data = await exchange_code_for_tokens(code)

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)
    scopes = token_data.get("scope", "")

    # Step 2: Fetch Google user profile
    user_info = await fetch_google_user_info(access_token)

    google_email = user_info.get("email", "")
    name = user_info.get("name", "")
    picture = user_info.get("picture", "")

    # Step 3: Save to temporary in-memory storage
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

    # Return safe account info (no tokens)
    return get_safe_google_account(user_id)


async def refresh_google_access_token(user_id: int) -> dict:
    """
    Refresh the Google access token using the stored refresh token.

    Sends a POST request to GOOGLE_TOKEN_URL with the refresh_token to obtain
    a new access_token. Updates the stored token data.

    Args:
        user_id: The application user ID.

    Returns:
        dict: Updated safe account information (without tokens).

    Raises:
        HTTPException: If no refresh token is available or if the refresh request fails.
    """
    account = get_google_account(user_id)
    refresh_token = account.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=400,
            detail="No refresh token available. Please reconnect your Google account "
                   "via GET /auth/google/login?user_id=" + str(user_id),
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
    Disconnect (remove) a Google account from temporary storage.

    Args:
        user_id: The application user ID.

    Returns:
        dict: Confirmation message.

    Raises:
        HTTPException: If no connected Google account is found for this user.
    """
    delete_google_account(user_id)
    return {"message": f"Google account disconnected for user_id={user_id}."}


def get_connected_google_account(user_id: int) -> dict:
    """
    Get the connected Google account information (safe, without tokens).

    This is safe to return directly in API responses.

    Args:
        user_id: The application user ID.

    Returns:
        dict: Safe account info without access_token or refresh_token.

    Raises:
        HTTPException: If no connected Google account is found for this user.
    """
    return get_safe_google_account(user_id)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTION DB-BACKED OAUTH FLOW
# These functions use the database (connected_accounts table) instead of
# the in-memory token store. Old functions above are kept for test routes.
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
    Build the Google OAuth authorization URL for production flow.
    No JWT required — this is a public endpoint.
    No user_id parameter — user identity comes from Google profile after callback.
    """
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": "v2",  # Identifies this as the v2 flow in callback
    }

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def connect_google_account_db(code: str, db: AsyncSession) -> dict:
    """
    Full production Google OAuth connection flow using database.

    Steps:
      1. Exchange authorization code for tokens.
      2. Fetch Google user profile (email, name, picture).
      3. Find or create user in `users` table.
      4. Upsert Google account in `connected_accounts` table.
      5. Ensure OmniBrain AI Drive folders exist.
      6. Generate application JWT.
      7. Return JWT and user info.

    Args:
        code: Authorization code from Google OAuth callback.
        db: Async database session.

    Returns:
        dict with access_token (JWT), user info.
    """
    # Step 1: Exchange code for Google tokens
    token_data = await exchange_code_for_tokens(code)

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)
    scopes = token_data.get("scope", "")

    # Step 2: Fetch Google profile
    user_info = await fetch_google_user_info(access_token)

    google_email = user_info.get("email", "")
    name = user_info.get("name", "")
    picture = user_info.get("picture", "")

    # Step 3: Find or create user
    user_repo = UserRepository(db)
    user, created = await user_repo.find_or_create_by_email(
        email=google_email,
        full_name=name,
        profile_picture=picture,
        auth_provider="google",
    )
    if created:
        logger.info(f"[GoogleAuth] New user created: id={user.id} email={google_email}")
    else:
        # Update profile info if changed
        if user.full_name != name or user.profile_picture != picture:
            await user_repo.update(user, {"full_name": name, "profile_picture": picture})
        logger.info(f"[GoogleAuth] Existing user found: id={user.id} email={google_email}")

    # Step 4: Upsert connected account
    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    account_repo = ConnectedAccountRepository(db)
    await account_repo.upsert_google_account(
        user_id=user.id,
        provider_email=google_email,
        provider_name=name,
        provider_picture=picture,
        access_token=access_token,
        refresh_token=refresh_token if refresh_token else None,
        token_expires_at=token_expires_at,
        scopes=scopes,
    )

    # Step 5: Ensure Drive folders exist
    try:
        await ensure_omnibrain_folders(user_id=user.id, db=db)
    except Exception as folder_exc:
        logger.warning(f"[GoogleAuth] Drive folder setup warning: {folder_exc}")
        # Don't fail the login if folder creation fails

    # Step 6: Generate application JWT
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

