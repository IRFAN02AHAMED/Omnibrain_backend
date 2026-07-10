"""
auth_service.py — Authentication Business Logic
================================================
Handles:
  - User login (verify credentials → return JWT tokens)
  - Token refresh (validate refresh token → return new access token)
  - User registration

RULES:
  - Service only talks to Repository and Security utilities
  - No DB queries here — all DB access goes through repositories
  - No HTTP concerns here — no Request/Response objects
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
)
from app.core.logger import logger
from app.repositories.user_repository import UserRepository
from app.repositories.document_repository import DocumentStatusRepository
from app.models.models import User
from app.schemas.schemas import LoginRequest, UserCreate
from fastapi import HTTPException, status


class AuthService:
    """
    Handles all authentication-related business logic.

    Injected dependencies:
        db: Async database session (via FastAPI Depends)
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Args:
            db: Injected async database session.
        """
        self._db   = db
        self._repo = UserRepository(db)

    async def login(self, credentials: LoginRequest) -> dict:
        """
        Authenticates a user and returns JWT tokens.

        Steps:
          1. Find user by email in the database
          2. Verify the provided password against the stored bcrypt hash
          3. Return access token + refresh token pair

        Args:
            credentials: LoginRequest with email and password.

        Returns:
            Dict with access_token, refresh_token, token_type, and user info.

        Raises:
            HTTPException 401: If credentials are wrong or account is inactive.
        """
        logger.info(f"[AuthService] Login attempt for: {credentials.email}")

        # Step 1: Find user
        user = await self._repo.get_by_email(credentials.email)
        if not user:
            logger.warning(f"[AuthService] Login failed — user not found: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        # Step 2: Verify password
        if not verify_password(credentials.password, user.password_hash):
            logger.warning(f"[AuthService] Login failed — wrong password: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        # Step 3: Generate tokens
        role_name = user.role.name if user.role else "viewer"
        access_token  = create_access_token(str(user.id), role_name)
        refresh_token = create_refresh_token(str(user.id))

        logger.info(f"[AuthService] Login successful for user: {user.id}")
        return {
            "access_token":  access_token,
            "refresh_token": refresh_token,
            "token_type":    "bearer",
            "user": {
                "id":    str(user.id),
                "name":  user.name,
                "email": user.email,
                "role":  role_name,
            },
        }

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Validates a refresh token and issues a new access token.

        Args:
            refresh_token: The long-lived refresh JWT string.

        Returns:
            Dict with new access_token.

        Raises:
            HTTPException 401: If refresh token is invalid or user is inactive.
        """
        logger.debug("[AuthService] Refreshing access token")

        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Please provide a refresh token.",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is missing user identity.",
            )

        user = await self._repo.get_by_id_with_role(UUID(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found or deactivated.",
            )

        role_name    = user.role.name if user.role else "viewer"
        access_token = create_access_token(str(user.id), role_name)

        logger.info(f"[AuthService] Token refreshed for user: {user.id}")
        return {"access_token": access_token, "token_type": "bearer"}

    async def register_user(self, data: UserCreate, created_by: UUID) -> User:
        """
        Creates a new user account.

        Args:
            data:       UserCreate schema with name, email, password, role_id.
            created_by: UUID of the admin performing the registration.

        Returns:
            Newly created User ORM instance.

        Raises:
            HTTPException 409: If the email is already registered.
        """
        logger.info(f"[AuthService] Registering new user: {data.email}")

        if await self._repo.email_exists(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{data.email}' is already registered.",
            )

        new_user = User(
            name=          data.name,
            email=         data.email.lower().strip(),
            password_hash= hash_password(data.password),
            role_id=       data.role_id,
            created_by=    created_by,
        )

        saved = await self._repo.create(new_user)
        logger.info(f"[AuthService] User registered successfully: {saved.id}")
        return saved
