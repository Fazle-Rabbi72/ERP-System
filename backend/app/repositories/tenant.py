"""Repository for the `tenants` table."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, Tenant)

    async def get_by_code(
        self,
        code: str,
        *,
        include_deleted: bool = False,
    ) -> Tenant | None:
        stmt = self._base_query(include_deleted=include_deleted).where(Tenant.code == code)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
