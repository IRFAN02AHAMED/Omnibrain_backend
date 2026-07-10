# app/core/google_config.py
# Purpose: Store all Google OAuth and Google API configuration.
# pip install google-api-python-client google-auth google-auth-oauthlib python-dotenv langgraph langchain-core

import os
from dotenv import load_dotenv

load_dotenv()

# ── Google OAuth Client Credentials ──────────────────────────────────────────
# These are obtained from Google Cloud Console > APIs & Credentials > OAuth 2.0 Client IDs.
# GOOGLE_CLIENT_SECRET should NEVER be exposed to the frontend.

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# ── Google OAuth Endpoints ───────────────────────────────────────────────────

# Authorization URL — where the user is redirected to log in with Google.
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

# Token URL — the Google endpoint used to exchange an authorization code
# for an access_token and refresh_token.
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# UserInfo URL — used to fetch the authenticated user's profile (email, name, picture).
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# ── Google OAuth Scopes ──────────────────────────────────────────────────────
# GOOGLE_SCOPES are the permissions requested from the Google user.
# Each scope grants access to a specific Google API or piece of user data.
# The user will see these permissions on the Google consent screen.

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]
