"""Repository for rotating `refresh_tokens`."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, RefreshToken)

    async def get_by_jti(self, jti: uuid.UUID) -> RefreshToken | None:
        stmt = self._base_query().where(RefreshToken.jti == jti)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_jti(
        self,
        jti: uuid.UUID,
        *,
        replaced_by_jti: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        now = datetime.now(UTC)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.tenant_id == self._tenant_id,
                RefreshToken.jti == jti,
                RefreshToken.revoked_at.is_(None),
            )
            .values(
                revoked_at=now,
                replaced_by_jti=replaced_by_jti,
                updated_at=now,
                updated_by=actor_id,
            )
        )
        await self._session.execute(stmt)

    async def revoke_family(
        self,
        family_id: uuid.UUID,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        now = datetime.now(UTC)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.tenant_id == self._tenant_id,
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now, updated_at=now, updated_by=actor_id)
        )
        await self._session.execute(stmt)

    async def revoke_all_for_user(
        self,
        user_id: uuid.UUID,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        now = datetime.now(UTC)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.tenant_id == self._tenant_id,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now, updated_at=now, updated_by=actor_id)
        )
        await self._session.execute(stmt)
