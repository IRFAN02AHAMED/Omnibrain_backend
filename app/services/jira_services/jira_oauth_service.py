from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logger import logger
from app.models.connected_account import ConnectedAccount
from app.repositories.connected_account_repository import ConnectedAccountRepository

ATLASSIAN_AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
ATLASSIAN_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
ATLASSIAN_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"

JIRA_SCOPES = "read:jira-work read:jira-user offline_access"


class JiraOAuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ConnectedAccountRepository(db)

    @staticmethod
    def get_authorize_url(oauth_state: str) -> str:
        params = {
            "audience": "api.atlassian.com",
            "client_id": settings.ATLASSIAN_CLIENT_ID,
            "scope": JIRA_SCOPES,
            "redirect_uri": settings.ATLASSIAN_REDIRECT_URI,
            "state": oauth_state,
            "response_type": "code",
            "prompt": "consent",
        }
        return f"{ATLASSIAN_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                ATLASSIAN_TOKEN_URL,
                json={
                    "grant_type": "authorization_code",
                    "client_id": settings.ATLASSIAN_CLIENT_ID,
                    "client_secret": settings.ATLASSIAN_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.ATLASSIAN_REDIRECT_URI,
                },
            )

        if response.status_code != 200:
            logger.error(f"Jira token exchange failed: {response.status_code} {response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange Jira authorization code for token.",
            )
        return response.json()

    async def fetch_accessible_resources(self, access_token: str) -> list:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                ATLASSIAN_RESOURCES_URL,
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )

        if response.status_code != 200:
            logger.error(f"Jira accessible resources failed: {response.status_code} {response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch accessible Jira sites.",
            )
        return response.json()

    async def handle_callback(self, code: str, user_id: int) -> ConnectedAccount:
        token_data = await self.exchange_code_for_token(code)
        resources = await self.fetch_accessible_resources(token_data["access_token"])

        if not resources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No accessible Jira sites found for this Atlassian account.",
            )

        site = resources[0]
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return await self.repo.upsert_connection(
            user_id=user_id,
            provider="jira",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_expires_at=expires_at,
            token_type="Bearer",
            scopes=token_data.get("scope") or JIRA_SCOPES,
            metadata_={
                "cloud_id": site.get("id"),
                "site_url": site.get("url"),
                "site_name": site.get("name"),
            },
        )

    async def refresh_access_token(self, connection: ConnectedAccount) -> ConnectedAccount:
        if not connection.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Jira refresh token found. Please reconnect Jira.",
            )

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                ATLASSIAN_TOKEN_URL,
                json={
                    "grant_type": "refresh_token",
                    "client_id": settings.ATLASSIAN_CLIENT_ID,
                    "client_secret": settings.ATLASSIAN_CLIENT_SECRET,
                    "refresh_token": connection.refresh_token,
                },
            )

        if response.status_code != 200:
            logger.error(f"Jira token refresh failed: {response.status_code} {response.text}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to refresh Jira token. Please reconnect Jira.",
            )

        token_data = response.json()
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return await self.repo.upsert_connection(
            user_id=connection.user_id,
            provider="jira",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", connection.refresh_token),
            token_expires_at=expires_at,
            token_type=connection.token_type or "Bearer",
            scopes=token_data.get("scope", connection.scopes),
            metadata_=connection.metadata_ or {},
        )
