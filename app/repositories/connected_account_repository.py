from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.connected_account import ConnectedAccount
from app.repositories.base_repository import BaseRepository

class ConnectedAccountRepository(BaseRepository[ConnectedAccount]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ConnectedAccount)

    async def get_by_user_id_and_provider(self, user_id: int, provider: str = "google") -> Optional[ConnectedAccount]:
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.provider == provider,
            self.model.is_active == True
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_google_account(self, user_id: int, provider_account_id: str, email: str, name: str, picture: str, token_data: dict) -> ConnectedAccount:
        account = await self.get_by_user_id_and_provider(user_id, "google")
        if not account:
            account = ConnectedAccount(
                user_id=user_id,
                provider="google",
                provider_account_id=provider_account_id,
                provider_email=email,
                provider_name=name,
                provider_picture=picture,
                access_token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type"),
                token_expires_at=token_data.get("expires_at"),
                scopes=",".join(token_data.get("scopes", [])) if isinstance(token_data.get("scopes"), list) else token_data.get("scopes")
            )
            return await self.create(account)
        else:
            update_data = {
                "provider_account_id": provider_account_id,
                "provider_email": email,
                "provider_name": name,
                "provider_picture": picture,
                "access_token": token_data.get("access_token") or account.access_token,
                "refresh_token": token_data.get("refresh_token") or account.refresh_token,
                "token_type": token_data.get("token_type") or account.token_type,
                "token_expires_at": token_data.get("expires_at") or account.token_expires_at,
                "scopes": ",".join(token_data.get("scopes", [])) if isinstance(token_data.get("scopes"), list) else (token_data.get("scopes") or account.scopes)
            }
            return await self.update(account, update_data)

    async def update_tokens(self, account: ConnectedAccount, access_token: str, expires_at: int) -> ConnectedAccount:
        return await self.update(account, {"access_token": access_token, "token_expires_at": expires_at})

    async def update_metadata(self, account: ConnectedAccount, metadata: Dict[str, Any]) -> ConnectedAccount:
        return await self.update(account, {"metadata_": metadata})

    async def get_google_account_for_user(self, user_id: int) -> Optional[ConnectedAccount]:
        return await self.get_by_user_id_and_provider(user_id, "google")
