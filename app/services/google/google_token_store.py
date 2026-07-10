# app/services/google/google_token_store.py
# Purpose: Temporary in-memory Google token storage for testing only.
# WARNING: This is NOT production storage. Data is lost on server restart.
# Later this will be replaced by the `connected_accounts` database table.

from fastapi import HTTPException


# ── In-Memory Storage ────────────────────────────────────────────────────────
# Format:
# CONNECTED_GOOGLE_ACCOUNTS = {
#     user_id: {
#         "google_email": "user@gmail.com",
#         "name": "John Doe",
#         "picture": "https://...",
#         "access_token": "ya29...",
#         "refresh_token": "1//...",
#         "expires_at": "3600",
#         "scopes": "openid email profile ..."
#     }
# }

CONNECTED_GOOGLE_ACCOUNTS: dict[int, dict] = {}


def save_google_account(
    user_id: int,
    google_email: str,
    name: str,
    picture: str,
    access_token: str,
    refresh_token: str,
    expires_at: str,
    scopes: str,
) -> None:
    """
    Save a connected Google account to temporary in-memory storage.

    Args:
        user_id: The application user ID.
        google_email: The user's Google email address.
        name: The user's Google display name.
        picture: URL to the user's Google profile picture.
        access_token: Google OAuth access token.
        refresh_token: Google OAuth refresh token.
        expires_at: Token expiration value (seconds or timestamp string).
        scopes: Space-separated string of granted OAuth scopes.
    """
    CONNECTED_GOOGLE_ACCOUNTS[user_id] = {
        "google_email": google_email,
        "name": name,
        "picture": picture,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "scopes": scopes,
    }


def get_google_account(user_id: int) -> dict:
    """
    Retrieve a connected Google account by user ID.

    Returns the FULL account dict including tokens.
    This is for INTERNAL use only — never return this directly in an API response.

    Args:
        user_id: The application user ID.

    Returns:
        dict: Full account information including tokens.

    Raises:
        HTTPException: If no connected Google account is found for this user.
    """
    account = CONNECTED_GOOGLE_ACCOUNTS.get(user_id)
    if not account:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No connected Google account found for user_id={user_id}. "
                f"Please connect first via GET /auth/google/login?user_id={user_id}"
            ),
        )
    return account


def get_google_account_by_email(google_email: str) -> dict | None:
    """
    Find a connected Google account by Google email address.

    Args:
        google_email: The Google email to search for.

    Returns:
        dict | None: Account information with user_id if found, None otherwise.
    """
    for uid, account in CONNECTED_GOOGLE_ACCOUNTS.items():
        if account.get("google_email") == google_email:
            return {"user_id": uid, **account}
    return None


def update_google_access_token(user_id: int, access_token: str, expires_at: str) -> None:
    """
    Update the access token for an existing connected Google account.

    Args:
        user_id: The application user ID.
        access_token: New Google OAuth access token.
        expires_at: New token expiration value.

    Raises:
        HTTPException: If no connected Google account is found for this user.
    """
    account = get_google_account(user_id)  # Raises HTTPException if not found
    account["access_token"] = access_token
    account["expires_at"] = expires_at


def delete_google_account(user_id: int) -> None:
    """
    Remove a connected Google account from temporary storage.

    Args:
        user_id: The application user ID.

    Raises:
        HTTPException: If no connected Google account is found for this user.
    """
    if user_id not in CONNECTED_GOOGLE_ACCOUNTS:
        raise HTTPException(
            status_code=404,
            detail=f"No connected Google account found for user_id={user_id}.",
        )
    del CONNECTED_GOOGLE_ACCOUNTS[user_id]


def get_safe_google_account(user_id: int) -> dict:
    """
    Retrieve connected Google account info WITHOUT tokens.

    This is safe to return in API responses.
    Does NOT include access_token or refresh_token.

    Args:
        user_id: The application user ID.

    Returns:
        dict: Account info without sensitive token fields.

    Raises:
        HTTPException: If no connected Google account is found for this user.
    """
    account = get_google_account(user_id)  # Raises HTTPException if not found
    return {
        "user_id": user_id,
        "google_email": account["google_email"],
        "name": account["name"],
        "picture": account["picture"],
        "scopes": account["scopes"],
        "connected": True,
    }
