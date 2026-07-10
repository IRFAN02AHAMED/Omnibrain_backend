from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.connected_account import ConnectedAccount
from app.repositories.connected_account_repository import ConnectedAccountRepository
from app.services.jira_services.jira_oauth_service import JiraOAuthService

JIRA_API_BASE = "https://api.atlassian.com/ex/jira"
TOKEN_EXPIRY_BUFFER_SECONDS = 60


class JiraConnectorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ConnectedAccountRepository(db)
        self.oauth_service = JiraOAuthService(db)

    async def get_status(self, user_id: int) -> dict:
        connection = await self.repo.get_by_user_and_provider(user_id, "jira")
        if not connection or not connection.is_connected:
            return {"connected": False}
        metadata = connection.metadata_ or {}
        return {
            "connected": True,
            "site_name": metadata.get("site_name"),
            "site_url": metadata.get("site_url"),
            "cloud_id": metadata.get("cloud_id"),
        }

    async def get_valid_connection(self, user_id: int) -> ConnectedAccount:
        connection = await self.repo.get_by_user_and_provider(user_id, "jira")
        if not connection or not connection.is_connected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Jira is not connected. Please connect Jira first.",
            )

        now = datetime.now(timezone.utc)
        if connection.token_expires_at:
            seconds_left = connection.token_expires_at.timestamp() - now.timestamp()
            if seconds_left < TOKEN_EXPIRY_BUFFER_SECONDS:
                logger.info(f"Refreshing Jira token for user {user_id}")
                connection = await self.oauth_service.refresh_access_token(connection)
        return connection

    async def get_projects(self, user_id: int) -> list:
        connection = await self.get_valid_connection(user_id)
        metadata = connection.metadata_ or {}
        cloud_id = metadata.get("cloud_id")
        if not cloud_id:
            raise HTTPException(status_code=400, detail="Jira cloud_id missing. Please reconnect Jira.")

        url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/project/search"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {connection.access_token}", "Accept": "application/json"},
            )

        if response.status_code != 200:
            logger.error(f"Jira projects fetch failed: {response.status_code} {response.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch Jira projects.")

        data = response.json()
        return [
            {
                "id": project.get("id"),
                "key": project.get("key"),
                "name": project.get("name"),
                "project_type": project.get("projectTypeKey"),
            }
            for project in data.get("values", [])
        ]
