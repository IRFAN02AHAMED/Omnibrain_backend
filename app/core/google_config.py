# app/core/google_config.py
# Purpose: Google OAuth configuration and API endpoints.

import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://127.0.0.1:8000/auth/google/callback",
)

GOOGLE_REDIRECT_URI_V2 = os.getenv(
    "GOOGLE_REDIRECT_URI_V2",
    "http://127.0.0.1:8000/auth/google/callback/v2",
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")



GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",

    # Full Drive access is needed for folder creation and file upload
    "https://www.googleapis.com/auth/drive",

    # Read-only access for Google Workspace content
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]