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
            logger.info("[JiraConnector] Exact issue lookup requested for %s", ticket_key)
            issue = await self.get_issue(user_id, ticket_key)
            return self._format_issue_context(issue)

        if self._is_issue_listing_query(query):
            projects = await self.get_projects(user_id)
            project = self._resolve_project_from_query(query, projects)
            if project:
                logger.info(
                    "[JiraConnector] Issue listing query matched project key=%s name=%s",
                    project.get("key"),
                    project.get("name"),
                )
                issues = await self.get_project_issues(user_id, project["key"])
                return self._format_project_issues_context(project, issues)
            logger.info("[JiraConnector] Issue listing query did not resolve to a specific project: %s", query)

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

    async def get_project_issues(self, user_id: int, project_key: str, max_results: int = 25) -> list[dict]:
        connection = await self.get_valid_connection(user_id)
        metadata = connection.metadata_ or {}
        cloud_id = metadata.get("cloud_id")
        if not cloud_id:
            raise HTTPException(status_code=400, detail="Jira cloud_id missing. Please reconnect Jira.")

        url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/search/jql"
        payload = {
            "jql": f'project = "{project_key}" ORDER BY created DESC',
            "maxResults": max_results,
            "fields": ["summary", "status", "assignee", "priority", "issuetype", "created", "updated"],
        }

        logger.info("[JiraConnector] Listing issues for project=%s via %s", project_key, url)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {connection.access_token}", "Accept": "application/json"},
                json=payload,
            )

        if response.status_code != 200:
            logger.error("Jira project issue listing failed for %s: %s %s", project_key, response.status_code, response.text)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to fetch Jira issues for project {project_key}.")

        data = response.json()
        return data.get("issues", [])

    def _extract_ticket_key(self, query: str) -> str | None:
        match = re.search(r"\b([A-Z][A-Z0-9]+-\d+)\b", query or "")
        if match:
            return match.group(1)
        return None

    def _is_issue_listing_query(self, query: str) -> bool:
        normalized = (query or "").lower()
        issue_keywords = ["ticket", "tickets", "issue", "issues", "bugs", "stories", "tasks"]
        return any(keyword in normalized for keyword in issue_keywords)

    def _resolve_project_from_query(self, query: str, projects: list[dict]) -> dict | None:
        if not projects:
            return None

        normalized_query = (query or "").lower()

        if "first project" in normalized_query or "1st project" in normalized_query:
            return projects[0]
        if "second project" in normalized_query or "2nd project" in normalized_query:
            return projects[1] if len(projects) > 1 else None

        compact_query = re.sub(r"[\s_-]+", "", normalized_query)
        for project in projects:
            project_key = (project.get("key") or "").lower()
            project_name = re.sub(r"[\s_-]+", "", (project.get("name") or "").lower())
            if project_key and project_key in normalized_query:
                return project
            if project_name and project_name in compact_query:
                return project

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

    def _format_project_issues_context(self, project: dict, issues: list[dict]) -> str:
        if not issues:
            return (
                f'Live Jira issue search returned no issues for project {project.get("name")} '
                f'({project.get("key")}).'
            )

        lines = [
            "Live Jira issue search result:",
            f'- Project: {project.get("name")} ({project.get("key")})',
            f"- Total issues returned in this response: {len(issues)}",
            "- Use these live Jira issues as grounded source data.",
            "",
            "Issues:",
        ]
        for issue in issues[:15]:
            fields = issue.get("fields") or {}
            status_name = ((fields.get("status") or {}).get("name")) or "Unknown"
            issue_type = ((fields.get("issuetype") or {}).get("name")) or "Unknown"
            assignee = ((fields.get("assignee") or {}).get("displayName")) or "Unassigned"
            priority = ((fields.get("priority") or {}).get("name")) or "Unknown"
            lines.append(
                f'- {issue.get("key")}: {fields.get("summary") or "No summary"} | '
                f'status: {status_name} | type: {issue_type} | priority: {priority} | assignee: {assignee}'
            )

        if len(issues) > 15:
            lines.append(f"- Plus {len(issues) - 15} more issue(s) not shown here.")

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
