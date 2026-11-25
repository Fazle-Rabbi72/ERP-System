"""Repository for tenant-scoped `users`."""

import uuid

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, User)

    async def get_by_email(
        self,
        email: str,
        *,
        include_deleted: bool = False,
    ) -> User | None:
        normalised = email.strip().lower()
        stmt = self._base_query(include_deleted=include_deleted).where(
            func.lower(User.email) == normalised
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
