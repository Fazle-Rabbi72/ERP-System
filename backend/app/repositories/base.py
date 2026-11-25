"""Generic tenant-scoped, soft-delete-aware repository.

Defense in depth: PostgreSQL RLS already enforces `tenant_id = app.tenant_id`,
and this repository ALSO filters every query by `tenant_id` and `is_deleted`
so that isolation never depends on a single layer.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.roles import ExpressionElementRole

from app.core.exceptions import PermissionDeniedError
from app.models.base import TenantBaseModel


class BaseRepository[ModelT: TenantBaseModel]:
    """Base CRUD repository for any `TenantBaseModel` subclass."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        model: type[ModelT],
    ) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._model = model

    @property
    def tenant_id(self) -> uuid.UUID:
        return self._tenant_id

    def _base_query(self, *, include_deleted: bool = False) -> Select[tuple[ModelT]]:
        stmt = select(self._model).where(self._model.tenant_id == self._tenant_id)
        if not include_deleted:
            stmt = stmt.where(self._model.is_deleted.is_(False))
        return stmt

    async def get_by_id(
        self,
        entity_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> ModelT | None:
        stmt = self._base_query(include_deleted=include_deleted).where(self._model.id == entity_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        filters: Sequence[ColumnElement[bool]] | None = None,
        order_by: Sequence[ExpressionElementRole[object]] | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[ModelT], int]:
        """Return a page of entities and the total matching count."""
        stmt = self._base_query(include_deleted=include_deleted)
        if filters:
            for condition in filters:
                stmt = stmt.where(condition)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self._session.execute(count_stmt)).scalar_one())

        if order_by:
            stmt = stmt.order_by(*order_by)
        else:
            stmt = stmt.order_by(self._model.created_at.desc(), self._model.id.desc())

        stmt = stmt.offset(offset).limit(limit)
        rows = list((await self._session.execute(stmt)).scalars().all())
        return rows, total

    async def create(
        self,
        entity: ModelT,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> ModelT:
        if entity.tenant_id is not None and entity.tenant_id != self._tenant_id:
            msg = "Cannot create a record belonging to another tenant."
            raise PermissionDeniedError(msg)
        entity.tenant_id = self._tenant_id
        if actor_id is not None:
            entity.created_by = actor_id
            entity.updated_by = actor_id
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(
        self,
        entity: ModelT,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> ModelT:
        if entity.tenant_id != self._tenant_id:
            msg = "Cannot update a record belonging to another tenant."
            raise PermissionDeniedError(msg)
        entity.updated_at = datetime.now(UTC)
        if actor_id is not None:
            entity.updated_by = actor_id
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def soft_delete(
        self,
        entity: ModelT,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> ModelT:
        if entity.tenant_id != self._tenant_id:
            msg = "Cannot delete a record belonging to another tenant."
            raise PermissionDeniedError(msg)
        entity.is_deleted = True
        entity.updated_at = datetime.now(UTC)
        if actor_id is not None:
            entity.updated_by = actor_id
        await self._session.flush()
        await self._session.refresh(entity)
        return entity
