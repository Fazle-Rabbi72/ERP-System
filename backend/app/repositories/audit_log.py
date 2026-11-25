"""Append-only repository for `audit_logs`. Intentionally has NO update or delete methods."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.roles import ExpressionElementRole

from app.core.exceptions import PermissionDeniedError
from app.models.audit_log import AuditLog


class AuditLogRepository:
    """Strictly append-only and read-only repository for immutable audit entries."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def append(self, entry: AuditLog) -> AuditLog:
        if entry.tenant_id is not None and entry.tenant_id != self._tenant_id:
            raise PermissionDeniedError("Cannot write an audit entry for another tenant.")
        entry.tenant_id = self._tenant_id
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry

    async def get_by_id(self, entry_id: uuid.UUID) -> AuditLog | None:
        stmt = select(AuditLog).where(
            AuditLog.tenant_id == self._tenant_id,
            AuditLog.id == entry_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_entries(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        filters: Sequence[ColumnElement[bool]] | None = None,
        order_by: Sequence[ExpressionElementRole[object]] | None = None,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog).where(AuditLog.tenant_id == self._tenant_id)
        if filters:
            for condition in filters:
                stmt = stmt.where(condition)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self._session.execute(count_stmt)).scalar_one())

        if order_by:
            stmt = stmt.order_by(*order_by)
        else:
            stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())

        stmt = stmt.offset(offset).limit(limit)
        rows = list((await self._session.execute(stmt)).scalars().all())
        return rows, total

