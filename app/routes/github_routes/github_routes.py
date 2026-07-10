from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token, get_current_user
from app.core.oauth_state import create_oauth_state, decode_oauth_state
from app.services.github_services.github_oauth_service import GitHubOAuthService
from app.services.github_services.github_connector_service import GitHubConnectorService
from app.utils.response import ResponseBuilder

router = APIRouter(prefix="/connectors/github", tags=["GitHub Connector"])


@router.get("/connect", summary="Start GitHub OAuth connection")
async def github_connect(token: str = Query(..., description="JWT access token from this app")):
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        return ResponseBuilder.error(message="Invalid or expired token.", status_code=401)
    oauth_state = create_oauth_state(user_id=user_id, provider="github")
    return RedirectResponse(GitHubOAuthService.get_authorize_url(oauth_state))


@router.get("/callback", summary="GitHub OAuth callback")
async def github_callback(code: str = Query(...), state: str = Query(...), db: AsyncSession = Depends(get_db)):
    state_data = decode_oauth_state(state, expected_provider="github")
    user_id = int(state_data["user_id"])
    service = GitHubOAuthService(db)
    connection = await service.handle_callback(code=code, user_id=user_id)
    metadata = connection.metadata_ or {}
    return RedirectResponse(
        url=(
            f"{settings.FRONTEND_URL}/chat"
            f"?connector=github&connected=1&username={metadata.get('github_username') or ''}"
        )
    )


@router.get("/status", summary="Check GitHub connection status")
async def github_status(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    data = await GitHubConnectorService(db).get_status(current_user.id)
    return ResponseBuilder.success(data=data, message="GitHub connection status fetched.")


@router.get("/repos", summary="List GitHub repositories")
async def github_repos(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    repos = await GitHubConnectorService(db).get_repos(current_user.id)
    return ResponseBuilder.success(data=repos, message="GitHub repositories fetched successfully.")
