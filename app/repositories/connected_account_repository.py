from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.connected_account import ConnectedAccount
from app.repositories.base_repository import BaseRepository


class ConnectedAccountRepository(BaseRepository[ConnectedAccount]):
    """Repository for Google/Jira/GitHub OAuth connections."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ConnectedAccount)

    async def get_by_user_id_and_provider(self, user_id: int, provider: str = "google") -> Optional[ConnectedAccount]:
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.provider == provider,
            self.model.is_active == True,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    
    async def get_by_user_id(
        self,
        user_id: int,
        provider: str = "google",
    ) -> Optional[ConnectedAccount]:
        """
        Backward-compatible alias used by Google Drive service.
        """
        return await self.get_by_user_id_and_provider(user_id, provider)
    
    async def get_by_user_and_provider(self, user_id: int, provider: str) -> Optional[ConnectedAccount]:
        """Alias used by Jira/GitHub connector services."""
        return await self.get_by_user_id_and_provider(user_id, provider)
    

    async def upsert_connection(
        self,
        user_id: int,
        provider: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expires_at: datetime | None = None,
        token_type: str | None = "Bearer",
        provider_account_id: str | None = None,
        provider_email: str | None = None,
        provider_name: str | None = None,
        provider_picture: str | None = None,
        scopes: str | None = None,
        metadata_: Dict[str, Any] | None = None,
    ) -> ConnectedAccount:
        """Create/update one OAuth row per (user_id, provider)."""
        account = await self.get_by_user_id_and_provider(user_id, provider)
        metadata_ = metadata_ or {}

        if account:
            account.access_token = access_token or account.access_token
            if refresh_token is not None:
                account.refresh_token = refresh_token
            account.token_expires_at = token_expires_at
            account.token_type = token_type or account.token_type
            account.provider_account_id = provider_account_id or account.provider_account_id
            account.provider_email = provider_email or account.provider_email
            account.provider_name = provider_name or account.provider_name
            account.provider_picture = provider_picture or account.provider_picture
            account.scopes = scopes or account.scopes
            account.metadata_ = metadata_ or account.metadata_ or {}
            account.is_connected = True
            account.is_active = True
            await self.db.commit()
            await self.db.refresh(account)
            return account

        account = ConnectedAccount(
            user_id=user_id,
            provider=provider,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            token_type=token_type,
            provider_account_id=provider_account_id,
            provider_email=provider_email,
            provider_name=provider_name,
            provider_picture=provider_picture,
            scopes=scopes,
            metadata_=metadata_,
            is_connected=True,
            is_active=True,
        )
        return await self.create(account)

    async def upsert_google_account(
        self,
        user_id: int,
        provider_account_id: str | None = None,
        provider_email: str | None = None,
        provider_name: str | None = None,
        provider_picture: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_type: str | None = "Bearer",
        token_expires_at: datetime | None = None,
        scopes: str | None = None,
        metadata_: Dict[str, Any] | None = None,
    ) -> ConnectedAccount:
        """
        Create/update Google OAuth connection in connected_accounts.

        This method matches the production Google OAuth service call.
        """
        return await self.upsert_connection(
            user_id=user_id,
            provider="google",
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            token_type=token_type,
            provider_account_id=provider_account_id,
            provider_email=provider_email,
            provider_name=provider_name,
            provider_picture=provider_picture,
            scopes=scopes,
            metadata_=metadata_ or {},
        )

    async def update_tokens(self, account: ConnectedAccount, access_token: str, expires_at) -> ConnectedAccount:
        account.access_token = access_token
        account.token_expires_at = expires_at
        account.is_connected = True
        account.is_active = True
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def update_metadata(self, account: ConnectedAccount, metadata: Dict[str, Any]) -> ConnectedAccount:
        account.metadata_ = metadata
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def get_google_account_for_user(self, user_id: int) -> Optional[ConnectedAccount]:
        return await self.get_by_user_id_and_provider(user_id, "google")

    async def disconnect(self, user_id: int, provider: str) -> bool:
        account = await self.get_by_user_id_and_provider(user_id, provider)
        if not account:
            return False
        account.is_connected = False
        account.is_active = False
        await self.db.commit()
        return True
