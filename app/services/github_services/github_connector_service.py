"""GitHub read-only API connector service."""

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.connected_account import ConnectedAccount
from app.repositories.connected_account_repository import ConnectedAccountRepository

GITHUB_API_BASE = "https://api.github.com"


class GitHubConnectorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ConnectedAccountRepository(db)

    async def get_status(self, user_id: int) -> dict:
        account = await self.repo.get_by_user_and_provider(user_id, "github")
        if not account or not account.is_connected:
            return {"connected": False}
        metadata = account.metadata_ or {}
        return {
            "connected": True,
            "github_username": metadata.get("github_username"),
            "provider_account_id": account.provider_account_id,
        }

    async def get_connection(self, user_id: int) -> ConnectedAccount:
        account = await self.repo.get_by_user_and_provider(user_id, "github")
        if not account or not account.is_connected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub is not connected. Please connect GitHub first.",
            )
        return account

    async def get_repos(self, user_id: int) -> list:
        account = await self.get_connection(user_id)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/user/repos",
                headers={"Authorization": f"Bearer {account.access_token}", "Accept": "application/vnd.github+json"},
                params={"per_page": 50, "sort": "updated"},
            )

        if response.status_code != 200:
            logger.error(f"GitHub repos fetch failed: {response.status_code} {response.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch GitHub repositories.")

        return [
            {
                "id": repo.get("id"),
                "name": repo.get("name"),
                "full_name": repo.get("full_name"),
                "private": repo.get("private"),
                "html_url": repo.get("html_url"),
                "default_branch": repo.get("default_branch"),
                "updated_at": repo.get("updated_at"),
            }
            for repo in response.json()
        ]
