# app/services/google/google_client_service.py
# Purpose: Create reusable Google API clients for Drive, Docs, Sheets, and Gmail.
# pip install google-api-python-client google-auth google-auth-oauthlib

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core.google_config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_TOKEN_URL,
    GOOGLE_SCOPES,
)


def create_google_credentials(account: dict) -> Credentials:
    """
    Create a Google Credentials object from stored account token data.

    The Credentials object is required by all Google API client libraries.
    It holds the access_token, refresh_token, and client info needed to
    authenticate and auto-refresh expired tokens.

    Args:
        account: Dictionary containing access_token, refresh_token, and other token data
                 (as stored in google_token_store).

    Returns:
        Credentials: A google.oauth2.credentials.Credentials instance ready for API calls.
    """
    return Credentials(
        token=account["access_token"],
        refresh_token=account.get("refresh_token"),
        token_uri=GOOGLE_TOKEN_URL,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=GOOGLE_SCOPES,
    )


def get_gmail_client(account: dict):
    """
    Create and return a Gmail API client (v1).

    Args:
        account: Dictionary containing Google account token data.

    Returns:
        googleapiclient.discovery.Resource: Gmail API service instance.
    """
    credentials = create_google_credentials(account)
    return build("gmail", "v1", credentials=credentials)


def get_drive_client(account: dict):
    """
    Create and return a Google Drive API client (v3).

    Args:
        account: Dictionary containing Google account token data.

    Returns:
        googleapiclient.discovery.Resource: Drive API service instance.
    """
    credentials = create_google_credentials(account)
    return build("drive", "v3", credentials=credentials)


def get_docs_client(account: dict):
    """
    Create and return a Google Docs API client (v1).

    Args:
        account: Dictionary containing Google account token data.

    Returns:
        googleapiclient.discovery.Resource: Docs API service instance.
    """
    credentials = create_google_credentials(account)
    return build("docs", "v1", credentials=credentials)


def get_sheets_client(account: dict):
    """
    Create and return a Google Sheets API client (v4).

    Args:
        account: Dictionary containing Google account token data.

    Returns:
        googleapiclient.discovery.Resource: Sheets API service instance.
    """
    credentials = create_google_credentials(account)
    return build("sheets", "v4", credentials=credentials)


# ─────────────────────────────────────────────────────────────────────────────
# DB-BACKED CLIENT BUILDERS (Production)
# These use google_token_service to get credentials from connected_accounts DB.
# The old dict-based builders above are kept for existing test routes.
# ─────────────────────────────────────────────────────────────────────────────

async def get_drive_client_for_user(user_id: int, db):
    """
    Create a Drive API client using DB-stored credentials.

    Args:
        user_id: Application user ID.
        db: Async database session.

    Returns:
        googleapiclient.discovery.Resource: Drive API service instance.
    """
    from app.services.google.google_token_service import get_user_google_credentials
    credentials = await get_user_google_credentials(user_id, db)
    return build("drive", "v3", credentials=credentials)


async def get_docs_client_for_user(user_id: int, db):
    """Create a Docs API client using DB-stored credentials."""
    from app.services.google.google_token_service import get_user_google_credentials
    credentials = await get_user_google_credentials(user_id, db)
    return build("docs", "v1", credentials=credentials)


async def get_sheets_client_for_user(user_id: int, db):
    """Create a Sheets API client using DB-stored credentials."""
    from app.services.google.google_token_service import get_user_google_credentials
    credentials = await get_user_google_credentials(user_id, db)
    return build("sheets", "v4", credentials=credentials)


async def get_gmail_client_for_user(user_id: int, db):
    """Create a Gmail API client using DB-stored credentials."""
    from app.services.google.google_token_service import get_user_google_credentials
    credentials = await get_user_google_credentials(user_id, db)
    return build("gmail", "v1", credentials=credentials)

