from datetime import datetime, timezone
import re

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
                detail="Jira is not connected for this user. Open Connectors and complete the Jira OAuth connection first.",
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

    async def get_context_for_query(self, user_id: int, query: str) -> str:
        ticket_key = self._extract_ticket_key(query)
        if ticket_key:
            issue = await self.get_issue(user_id, ticket_key)
            return self._format_issue_context(issue)

        projects = await self.get_projects(user_id)
        if not projects:
            return "Jira is connected, but no projects were returned for this account."

        lines = ["Jira projects available for this user:"]
        for project in projects[:5]:
            lines.append(
                f"- {project.get('key')}: {project.get('name')} | type: {project.get('project_type')}"
            )
        if len(projects) > 5:
            lines.append(f"- Plus {len(projects) - 5} more projects not shown here.")
        return "\n".join(lines)

    async def get_issue(self, user_id: int, issue_key: str) -> dict:
        connection = await self.get_valid_connection(user_id)
        metadata = connection.metadata_ or {}
        cloud_id = metadata.get("cloud_id")
        if not cloud_id:
            raise HTTPException(status_code=400, detail="Jira cloud_id missing. Please reconnect Jira.")

        url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/issue/{issue_key}"
        params = {
            "fields": "summary,description,status,assignee,reporter,priority,issuetype,project,created,updated",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {connection.access_token}", "Accept": "application/json"},
                params=params,
            )

        if response.status_code != 200:
            logger.error(f"Jira issue fetch failed: {response.status_code} {response.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch Jira issue details.")

        return response.json()

    def _extract_ticket_key(self, query: str) -> str | None:
        match = re.search(r"\b([A-Z][A-Z0-9]+-\d+)\b", query or "")
        if match:
            return match.group(1)
        return None

    def _format_issue_context(self, issue: dict) -> str:
        fields = issue.get("fields") or {}
        description = self._extract_description_text(fields.get("description"))
        assignee = (fields.get("assignee") or {}).get("displayName")
        reporter = (fields.get("reporter") or {}).get("displayName")
        priority = (fields.get("priority") or {}).get("name")
        issue_type = (fields.get("issuetype") or {}).get("name")
        project = (fields.get("project") or {}).get("name")
        status_name = (fields.get("status") or {}).get("name")

        lines = [
            f"Jira ticket details for {issue.get('key')}:",
            f"- Summary: {fields.get('summary') or 'No summary provided.'}",
            f"- Status: {status_name or 'Unknown'}",
            f"- Issue type: {issue_type or 'Unknown'}",
            f"- Priority: {priority or 'Unknown'}",
            f"- Project: {project or 'Unknown'}",
            f"- Assignee: {assignee or 'Unassigned'}",
            f"- Reporter: {reporter or 'Unknown'}",
            f"- Created: {fields.get('created')}",
            f"- Updated: {fields.get('updated')}",
        ]

        if description:
            lines.append(f"- Description: {description}")

        return "\n".join(lines)

    def _extract_description_text(self, description: dict | None) -> str:
        if not description or not isinstance(description, dict):
            return ""

        parts: list[str] = []

        def walk(node: dict) -> None:
            if not isinstance(node, dict):
                return
            if "text" in node and isinstance(node["text"], str):
                parts.append(node["text"])
            for child in node.get("content", []) or []:
                if isinstance(child, dict):
                    walk(child)

        walk(description)
        return " ".join(part.strip() for part in parts if part.strip())[:1000]
