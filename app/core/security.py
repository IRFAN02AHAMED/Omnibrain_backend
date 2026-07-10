"""
security.py — JWT & Password Security Utilities
================================================
Provides:
  - Password hashing (bcrypt via passlib)
  - JWT access token creation
  - JWT refresh token creation
  - JWT token decoding & validation
  - FastAPI dependency for current authenticated user

HOW TO USE:
    from app.core.security import (
        hash_password, verify_password,
        create_access_token, create_refresh_token,
        get_current_user
    )
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logger import logger


# ── Password hashing context (bcrypt) ─────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"])

# ── OAuth2 scheme — tells FastAPI where to look for the token ─────────────────
# FastAPI reads token using OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/google/login/v2")


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.

    Args:
        plain_password: The raw password from the user.

    Returns:
        Bcrypt hash string safe for database storage.
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compares a plain-text password against a stored bcrypt hash.

    Args:
        plain_password:  Raw password entered by the user at login.
        hashed_password: Stored bcrypt hash from the database.

    Returns:
        True if they match, False otherwise.
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN CREATION
# ─────────────────────────────────────────────────────────────────────────────

def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    """
    Internal helper that creates a signed JWT with an expiry time.

    Args:
        data:           Dictionary of claims to embed in the token.
        expires_delta:  How long until the token expires.

    Returns:
        Signed JWT string.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    payload["exp"] = expire
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, role_name: str = "user") -> str:
    """
    Creates a short-lived JWT access token for authenticating API requests.

    Args:
        user_id:   ID of the authenticated user (as string).
        role_name: User's role name (default: "user").

    Returns:
        Signed JWT access token string.
    """
    return _create_token(
        data={"sub": user_id, "role": role_name, "type": "access"},
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    """
    Creates a long-lived JWT refresh token used to obtain new access tokens.

    Args:
        user_id: ID of the authenticated user (as string).

    Returns:
        Signed JWT refresh token string.
    """
    return _create_token(
        data={"sub": user_id, "type": "refresh"},
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decodes and validates a JWT token.

    Args:
        token: Signed JWT string.

    Returns:
        Decoded payload dictionary.

    Raises:
        HTTPException 401 if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        logger.warning(f"JWT decode failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI DEPENDENCIES
# ─────────────────────────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    FastAPI dependency that extracts and returns the currently logged-in user.

    Steps:
      1. Read Bearer token from Authorization header.
      2. Decode & validate JWT.
      3. Load the user row from PostgreSQL.
      4. Raise 401 if user not found or inactive.

    Returns:
        The authenticated User ORM object.

    Usage in routes:
        async def my_route(current_user = Depends(get_current_user)):
            ...
    """
    # Import here to avoid circular imports (models import Base from database)
    from app.repositories.user_repository import UserRepository

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Please use an access token.",
        )

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing user identity.",
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identity in token.",
        )

    repo = UserRepository(db)
    user = await repo.get_by_id_int(user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or has been deactivated.",
        )

    return user
