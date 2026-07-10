"""GitHub OAuth connector service.

Classic GitHub OAuth App tokens do not expire and do not have refresh tokens.
Read-only behavior is enforced by our code: this service and connector service only use GET/ OAuth calls.
"""

from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logger import logger
from app.models.connected_account import ConnectedAccount
from app.repositories.connected_account_repository import ConnectedAccountRepository

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_SCOPES = "read:user repo"


class GitHubOAuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ConnectedAccountRepository(db)

    @staticmethod
    def get_authorize_url(oauth_state: str) -> str:
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
            "scope": GITHUB_SCOPES,
            "state": oauth_state,
            "allow_signup": "false",
        }
        return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.GITHUB_REDIRECT_URI,
                },
            )

        data = response.json()
        if response.status_code != 200 or "access_token" not in data:
            logger.error(f"GitHub token exchange failed: {response.status_code} {data}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange GitHub authorization code: {data.get('error_description', data)}",
            )
        return data

    async def fetch_github_user(self, access_token: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                GITHUB_USER_URL,
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            )

        if response.status_code != 200:
            logger.error(f"GitHub user fetch failed: {response.status_code} {response.text}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch GitHub user profile.")
        return response.json()

    async def handle_callback(self, code: str, user_id: int) -> ConnectedAccount:
        token_data = await self.exchange_code_for_token(code)
        access_token = token_data["access_token"]
        github_user = await self.fetch_github_user(access_token)

        account = await self.repo.upsert_connection(
            user_id=user_id,
            provider="github",
            access_token=access_token,
            refresh_token=None,
            token_expires_at=None,
            token_type="Bearer",
            provider_account_id=str(github_user.get("id")) if github_user.get("id") is not None else None,
            provider_email=github_user.get("email"),
            provider_name=github_user.get("name"),
            provider_picture=github_user.get("avatar_url"),
            scopes=token_data.get("scope") or GITHUB_SCOPES,
            metadata_={"github_username": github_user.get("login")},
        )
        logger.info(f"GitHub connected for user {user_id}: @{github_user.get('login')}")
        return account
