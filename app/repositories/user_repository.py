from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.repositories.base_repository import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(self.model).where(
            self.model.email == email,
            self.model.is_active == True
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_google_user(self, email: str, full_name: Optional[str], profile_picture: Optional[str]) -> User:
        user = User(
            email=email,
            full_name=full_name,
            profile_picture=profile_picture,
            auth_provider="google"
        )
        return await self.create(user)

    async def find_or_create_by_email(self, email: str, full_name: Optional[str], profile_picture: Optional[str]) -> User:
        user = await self.get_by_email(email)
        if not user:
            user = await self.create_google_user(email, full_name, profile_picture)
        return user
