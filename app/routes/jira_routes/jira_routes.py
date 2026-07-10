from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.oauth_state import create_oauth_state, decode_oauth_state
from app.core.security import decode_token, get_current_user
from app.services.jira_services.jira_connector_service import JiraConnectorService
from app.services.jira_services.jira_oauth_service import JiraOAuthService
from app.utils.response import ResponseBuilder

router = APIRouter(prefix="/connectors/jira", tags=["Jira Connector"])


@router.get("/connect", summary="Start Jira OAuth connection")
async def jira_connect(token: str = Query(..., description="JWT access token from this app")):
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        return ResponseBuilder.error(message="Invalid or expired token.", status_code=401)
    oauth_state = create_oauth_state(user_id=user_id, provider="jira")
    return RedirectResponse(JiraOAuthService.get_authorize_url(oauth_state))


@router.get("/callback", summary="Jira OAuth callback")
async def jira_callback(code: str = Query(...), state: str = Query(...), db: AsyncSession = Depends(get_db)):
    state_data = decode_oauth_state(state, expected_provider="jira")
    user_id = int(state_data["user_id"])
    service = JiraOAuthService(db)
    connection = await service.handle_callback(code=code, user_id=user_id)
    metadata = connection.metadata_ or {}
    return RedirectResponse(
        url=(
            f"{settings.FRONTEND_URL}/chat"
            f"?connector=jira&connected=1&site={metadata.get('site_name') or ''}"
        )
    )


@router.get("/status", summary="Check Jira connection status")
async def jira_status(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    data = await JiraConnectorService(db).get_status(current_user.id)
    return ResponseBuilder.success(data=data, message="Jira connection status fetched successfully.")


@router.get("/projects", summary="List Jira projects")
async def jira_projects(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    projects = await JiraConnectorService(db).get_projects(current_user.id)
    return ResponseBuilder.success(data=projects, message="Jira projects fetched successfully.")


@router.get("/projects/{project_key}/issues", summary="List Jira issues for a project")
async def jira_project_issues(
    project_key: str,
    max_results: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    issues = await JiraConnectorService(db).get_project_issues(current_user.id, project_key.upper(), max_results=max_results)
    return ResponseBuilder.success(
        data=issues,
        message=f"Jira issues fetched successfully for project {project_key.upper()}.",
    )
