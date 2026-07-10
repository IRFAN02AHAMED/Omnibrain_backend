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
                detail="GitHub is not connected for this user. Open Connectors and complete the GitHub OAuth connection first.",
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

    async def get_context_for_query(self, user_id: int, query: str) -> str:
        repos = await self.get_repos(user_id)
        if not repos:
            return "GitHub is connected, but no repositories were returned for this account."

        normalized_query = (query or "").strip().lower()
        matched_repos = [
            repo for repo in repos
            if repo.get("name", "").lower() in normalized_query
            or repo.get("full_name", "").lower() in normalized_query
        ]

        if matched_repos:
            repo = matched_repos[0]
            details = await self.get_repo_details(user_id, repo["full_name"])
            return self._format_repo_context(details)

        top_repos = repos[:5]
        lines = ["GitHub repositories available for this user:"]
        for repo in top_repos:
            visibility = "private" if repo.get("private") else "public"
            lines.append(
                f"- {repo.get('full_name')} ({visibility}) | default branch: {repo.get('default_branch')} | "
                f"updated: {repo.get('updated_at')} | url: {repo.get('html_url')}"
            )

        if len(repos) > len(top_repos):
            lines.append(f"- Plus {len(repos) - len(top_repos)} more repositories not shown here.")

        return "\n".join(lines)

    async def get_repo_details(self, user_id: int, full_name: str) -> dict:
        account = await self.get_connection(user_id)
        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            repo_response = await client.get(f"{GITHUB_API_BASE}/repos/{full_name}", headers=headers)
            pulls_response = await client.get(
                f"{GITHUB_API_BASE}/repos/{full_name}/pulls",
                headers=headers,
                params={"state": "open", "per_page": 3},
            )
            commits_response = await client.get(
                f"{GITHUB_API_BASE}/repos/{full_name}/commits",
                headers=headers,
                params={"per_page": 3},
            )

        if repo_response.status_code != 200:
            logger.error("GitHub repo details fetch failed: %s %s", repo_response.status_code, repo_response.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch GitHub repository details.",
            )

        repo = repo_response.json()
        pulls = pulls_response.json() if pulls_response.status_code == 200 else []
        commits = commits_response.json() if commits_response.status_code == 200 else []

        return {
            "repo": {
                "name": repo.get("name"),
                "full_name": repo.get("full_name"),
                "description": repo.get("description"),
                "private": repo.get("private"),
                "default_branch": repo.get("default_branch"),
                "language": repo.get("language"),
                "stargazers_count": repo.get("stargazers_count"),
                "open_issues_count": repo.get("open_issues_count"),
                "updated_at": repo.get("updated_at"),
                "html_url": repo.get("html_url"),
            },
            "open_pulls": [
                {
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "state": pr.get("state"),
                    "html_url": pr.get("html_url"),
                    "updated_at": pr.get("updated_at"),
                }
                for pr in pulls
            ],
            "recent_commits": [
                {
                    "sha": (commit.get("sha") or "")[:7],
                    "message": ((commit.get("commit") or {}).get("message") or "").split("\n")[0],
                    "author": ((commit.get("commit") or {}).get("author") or {}).get("name"),
                    "date": ((commit.get("commit") or {}).get("author") or {}).get("date"),
                    "html_url": commit.get("html_url"),
                }
                for commit in commits
            ],
        }

    def _format_repo_context(self, details: dict) -> str:
        repo = details.get("repo", {})
        lines = [
            f"GitHub repository details for {repo.get('full_name')}:",
            f"- Description: {repo.get('description') or 'No description provided.'}",
            f"- Visibility: {'private' if repo.get('private') else 'public'}",
            f"- Default branch: {repo.get('default_branch')}",
            f"- Primary language: {repo.get('language') or 'Unknown'}",
            f"- Stars: {repo.get('stargazers_count')}",
            f"- Open issues count: {repo.get('open_issues_count')}",
            f"- Last updated: {repo.get('updated_at')}",
            f"- URL: {repo.get('html_url')}",
        ]

        open_pulls = details.get("open_pulls") or []
        if open_pulls:
            lines.append("- Open pull requests:")
            for pr in open_pulls:
                lines.append(
                    f"  - PR #{pr.get('number')}: {pr.get('title')} | updated: {pr.get('updated_at')} | {pr.get('html_url')}"
                )

        recent_commits = details.get("recent_commits") or []
        if recent_commits:
            lines.append("- Recent commits:")
            for commit in recent_commits:
                lines.append(
                    f"  - {commit.get('sha')}: {commit.get('message')} by {commit.get('author')} on {commit.get('date')}"
                )

        return "\n".join(lines)
