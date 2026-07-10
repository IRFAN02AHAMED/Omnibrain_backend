# app/routes/google/google_auth_routes.py
# Purpose: Google OAuth routes for login, callback, account info, token refresh, and disconnect.

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import RedirectResponse

from app.services.google.google_auth_service import (
    build_google_login_url,
    connect_google_account,
    refresh_google_access_token,
    disconnect_google_account,
    get_connected_google_account,
    build_google_login_url_v2,
    connect_google_account_db,
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.google_config import FRONTEND_URL
from app.core.security import get_current_user
from app.models.user import User

# ─────────────────────────────────────────────────────────────────────────────
# TODO: Replace `user_id` query parameter / state with current logged-in user
#       from JWT dependency later. For now, user_id is accepted as a query
#       parameter for beginner testing.
# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/auth/google", tags=["Google Auth"])


@router.get("/login")
async def google_login(
    user_id: int = Query(None, description="Temporary user ID for testing (sent as OAuth state)"),
):
    """
    Redirect the user to Google OAuth login page.

    If user_id is provided, it is embedded in the OAuth `state` parameter
    so the callback can identify which application user is connecting.

    Example:
        GET /auth/google/login?user_id=1
    """
    login_url = build_google_login_url(user_id=user_id)
    return RedirectResponse(url=login_url)


@router.get("/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(None, description="OAuth state parameter (contains user_id)"),
    user_id: int = Query(None, description="Temporary user_id override for testing"),
):
    """
    Handle Google OAuth callback after the user completes Google login.

    Google redirects here with `code` and optional `state`.
    Resolves user identity in this priority order:
      1. user_id query parameter (if provided directly)
      2. state parameter (set during login via /auth/google/login?user_id=X)
      3. Error — asks user to start login with user_id

    Example:
        GET /auth/google/callback?code=4/0A...&state=1
    """
    # TODO: Replace this with JWT/session-based user identification later.

    # Resolve final user_id from available sources
    final_user_id = user_id

    if final_user_id is None and state:
        try:
            final_user_id = int(state)
        except (ValueError, TypeError):
            final_user_id = None

    if final_user_id is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not determine user_id from callback. "
                "Please start login with: GET /auth/google/login?user_id=YOUR_ID"
            ),
        )

    result = await connect_google_account(user_id=final_user_id, code=code)
    return {"message": "Google account connected successfully.", "account": result}


@router.get("/me")
async def google_me(
    user_id: int = Query(..., description="User ID to look up"),
):
    """
    Get the connected Google account information for a user.

    Returns account details WITHOUT access_token or refresh_token.

    Example:
        GET /auth/google/me?user_id=1
    """
    # TODO: Replace `user_id` with current logged-in user from JWT dependency.
    return get_connected_google_account(user_id)


@router.get("/me/v2")
async def google_me_v2(current_user: User = Depends(get_current_user)):
    """
    Return the currently authenticated application user from the JWT token.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "profile_picture": current_user.profile_picture,
        "auth_provider": current_user.auth_provider,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }


@router.post("/refresh-token")
async def google_refresh_token(
    user_id: int = Query(..., description="User ID"),
):
    """
    Refresh the Google access token for a connected account.

    Uses the stored refresh_token to obtain a new access_token from Google.

    Example:
        POST /auth/google/refresh-token?user_id=1
    """
    # TODO: Replace `user_id` with current logged-in user from JWT dependency.
    return await refresh_google_access_token(user_id)


@router.delete("/disconnect")
async def google_disconnect(
    user_id: int = Query(..., description="User ID"),
):
    """
    Disconnect (remove) the Google account for a user.

    Removes the stored tokens from temporary in-memory storage.

    Example:
        DELETE /auth/google/disconnect?user_id=1
    """
    # TODO: Replace `user_id` with current logged-in user from JWT dependency.
    return disconnect_google_account(user_id)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTION OAUTH v2 ROUTES (JWT-BASED)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/login/v2")
async def google_login_v2():
    """
    Redirect the user to Google OAuth login page (Production Flow).
    No user_id required.
    """
    login_url = build_google_login_url_v2()
    return RedirectResponse(url=login_url)


@router.get("/callback/v2")
async def google_callback_v2(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(None, description="OAuth state parameter (should be 'v2')"),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback (Production Flow).
    Receives code, saves user in DB, creates JWT, and redirects to frontend.
    """
    try:
        result = await connect_google_account_db(code, db)
        access_token = result.get("access_token")
        
        # Redirect back to frontend with the JWT in URL query
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?token={access_token}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=400,
            detail=f"Google OAuth v2 connection failed: {str(e)}",
        )
