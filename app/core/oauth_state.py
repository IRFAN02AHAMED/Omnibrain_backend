"""Short-lived signed OAuth state helpers for connector OAuth flows."""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

OAUTH_STATE_EXPIRE_MINUTES = 10


def create_oauth_state(user_id: int | str, provider: str) -> str:
    """Create a short-lived JWT used as OAuth `state`."""
    payload = {
        "user_id": str(user_id),
        "provider": provider,
        "type": "oauth_state",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=OAUTH_STATE_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_oauth_state(state: str, expected_provider: str) -> dict[str, Any]:
    """Decode and validate OAuth state returned by Jira/GitHub."""
    try:
        payload = jwt.decode(state, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state is invalid or expired. Please try connecting again.",
        )

    if payload.get("type") != "oauth_state":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state type.")

    if payload.get("provider") != expected_provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state provider mismatch.")

    return payload
