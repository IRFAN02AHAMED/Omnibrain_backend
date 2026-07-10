from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
    return ResponseBuilder.success(
        data={
            "connected": True,
            "site_name": metadata.get("site_name"),
            "site_url": metadata.get("site_url"),
            "cloud_id": metadata.get("cloud_id"),
        },
        message="Jira connected successfully. You can close this tab.",
    )


@router.get("/status", summary="Check Jira connection status")
async def jira_status(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    data = await JiraConnectorService(db).get_status(current_user.id)
    return ResponseBuilder.success(data=data, message="Jira connection status fetched successfully.")


@router.get("/projects", summary="List Jira projects")
async def jira_projects(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    projects = await JiraConnectorService(db).get_projects(current_user.id)
    return ResponseBuilder.success(data=projects, message="Jira projects fetched successfully.")
