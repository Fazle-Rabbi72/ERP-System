"""Repositories for RBAC tables (roles, permissions, assignments)."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.repositories.base import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, Permission)

    async def get_by_code(self, code: str) -> Permission | None:
        stmt = self._base_query().where(Permission.code == code)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_codes(self, codes: Sequence[str]) -> list[Permission]:
        if not codes:
            return []
        stmt = self._base_query().where(Permission.code.in_(codes))
        return list((await self._session.execute(stmt)).scalars().all())


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, Role)

    async def get_by_code(self, code: str) -> Role | None:
        stmt = self._base_query().where(Role.code == code)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_permission_codes_for_role(self, role_id: uuid.UUID) -> list[str]:
        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(
                RolePermission.tenant_id == self._tenant_id,
                RolePermission.role_id == role_id,
                RolePermission.is_deleted.is_(False),
                Permission.tenant_id == self._tenant_id,
                Permission.is_deleted.is_(False),
            )
            .order_by(Permission.code.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_effective_permissions_for_user(self, user_id: uuid.UUID) -> set[str]:
        """Return all active permission codes granted to `user_id` via any assigned role."""
        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.tenant_id == self._tenant_id,
                UserRole.user_id == user_id,
                UserRole.is_deleted.is_(False),
                Role.tenant_id == self._tenant_id,
                Role.is_deleted.is_(False),
                RolePermission.tenant_id == self._tenant_id,
                RolePermission.is_deleted.is_(False),
                Permission.tenant_id == self._tenant_id,
                Permission.is_deleted.is_(False),
            )
            .distinct()
        )
        return set((await self._session.execute(stmt)).scalars().all())

    async def attach_permissions(
        self,
        role_id: uuid.UUID,
        permission_ids: Sequence[uuid.UUID],
        *,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        rp_repo = BaseRepository(self._session, self._tenant_id, RolePermission)
        existing_stmt = select(RolePermission).where(
            RolePermission.tenant_id == self._tenant_id,
            RolePermission.role_id == role_id,
        )
        existing = {
            rp.permission_id: rp for rp in (await self._session.execute(existing_stmt)).scalars()
        }
        for perm_id in permission_ids:
            row = existing.get(perm_id)
            if row is None:
                await rp_repo.create(
                    RolePermission(
                        tenant_id=self._tenant_id,
                        role_id=role_id,
                        permission_id=perm_id,
                    ),
                    actor_id=actor_id,
                )
            elif row.is_deleted:
                row.is_deleted = False
                await rp_repo.update(row, actor_id=actor_id)

    async def assign_to_user(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        ur_repo = BaseRepository(self._session, self._tenant_id, UserRole)
        stmt = select(UserRole).where(
            UserRole.tenant_id == self._tenant_id,
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            await ur_repo.create(
                UserRole(tenant_id=self._tenant_id, user_id=user_id, role_id=role_id),
                actor_id=actor_id,
            )
        elif existing.is_deleted:
            existing.is_deleted = False
            await ur_repo.update(existing, actor_id=actor_id)

    async def revoke_from_user(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> bool:
        ur_repo = BaseRepository(self._session, self._tenant_id, UserRole)
        stmt = select(UserRole).where(
            UserRole.tenant_id == self._tenant_id,
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.is_deleted.is_(False),
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            return False
        await ur_repo.soft_delete(existing, actor_id=actor_id)
        return True
