"""RBAC service: permission checks, role management, and tenant RBAC seeding."""

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Database
from app.core.exceptions import ConflictError, DomainValidationError, NotFoundError
from app.core.logging import get_logger
from app.core.permissions import BASELINE_PERMISSIONS, BASELINE_ROLES
from app.core.query import (
    FilterRule,
    PaginationParams,
    SortParams,
    build_filters,
    build_order_by,
)
from app.models.rbac import Permission, Role
from app.repositories.rbac import PermissionRepository, RoleRepository
from app.repositories.user import UserRepository

logger = get_logger(__name__)


async def seed_tenant_rbac(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
) -> dict[str, Role]:
    """Idempotently ensure baseline permissions and system roles exist for a tenant."""
    perm_repo = PermissionRepository(session, tenant_id)
    role_repo = RoleRepository(session, tenant_id)

    perm_map: dict[str, Permission] = {}
    for pdef in BASELINE_PERMISSIONS:
        existing = await perm_repo.get_by_code(pdef.code)
        if existing is None:
            existing = await perm_repo.create(
                Permission(
                    tenant_id=tenant_id,
                    code=pdef.code,
                    module=pdef.module,
                    description=pdef.description,
                ),
                actor_id=actor_id,
            )
        perm_map[pdef.code] = existing

    role_map: dict[str, Role] = {}
    for rdef in BASELINE_ROLES:
        role = await role_repo.get_by_code(rdef.code)
        if role is None:
            role = await role_repo.create(
                Role(
                    tenant_id=tenant_id,
                    code=rdef.code,
                    name=rdef.name,
                    description=rdef.description,
                    is_system=True,
                ),
                actor_id=actor_id,
            )
        perm_ids = [perm_map[code].id for code in rdef.permissions if code in perm_map]
        await role_repo.attach_permissions(role.id, perm_ids, actor_id=actor_id)
        role_map[rdef.code] = role

    return role_map


class RbacService:
    """All RBAC business rules live here."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def get_user_permissions(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> set[str]:
        async with self._database.transaction(tenant_id) as session:
            return await RoleRepository(session, tenant_id).get_effective_permissions_for_user(
                user_id
            )

    async def user_has_permissions(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        required: Sequence[str],
    ) -> bool:
        if not required:
            return True
        effective = await self.get_user_permissions(tenant_id, user_id)
        return all(code in effective for code in required)

    async def list_roles(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        search: str | None = None,
    ) -> tuple[list[Role], int]:
        order_by = build_order_by(
            sort,
            allowed={"code": Role.code, "name": Role.name, "created_at": Role.created_at},
            default=[Role.code.asc()],
        )
        filters = build_filters([FilterRule(column=Role.name, operator="ilike", value=search)])
        async with self._database.transaction(tenant_id) as session:
            return await RoleRepository(session, tenant_id).list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def list_permissions(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        module: str | None = None,
    ) -> tuple[list[Permission], int]:
        order_by = build_order_by(
            sort,
            allowed={"code": Permission.code, "module": Permission.module},
            default=[Permission.module.asc(), Permission.code.asc()],
        )
        filters = build_filters([FilterRule(column=Permission.module, operator="eq", value=module)])
        async with self._database.transaction(tenant_id) as session:
            return await PermissionRepository(session, tenant_id).list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def create_role(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        code: str,
        name: str,
        description: str,
        permission_codes: Sequence[str],
    ) -> Role:
        normalised_code = code.strip().lower()
        async with self._database.transaction(tenant_id) as session:
            role_repo = RoleRepository(session, tenant_id)
            perm_repo = PermissionRepository(session, tenant_id)

            if await role_repo.get_by_code(normalised_code) is not None:
                raise ConflictError("A role with this code already exists.")

            unique_codes = sorted(set(permission_codes))
            perms = await perm_repo.get_by_codes(unique_codes)
            found_codes = {p.code for p in perms}
            unknown = sorted(set(unique_codes) - found_codes)
            if unknown:
                raise DomainValidationError(
                    "One or more permission codes are unknown.",
                    details={"unknown_permissions": list(unknown)},
                )

            role = await role_repo.create(
                Role(
                    tenant_id=tenant_id,
                    code=normalised_code,
                    name=name.strip(),
                    description=description.strip(),
                    is_system=False,
                ),
                actor_id=actor_id,
            )
            await role_repo.attach_permissions(role.id, [p.id for p in perms], actor_id=actor_id)
        logger.info(
            "role_created", tenant_id=str(tenant_id), actor_id=str(actor_id), role=role.code
        )
        return role

    async def assign_role_to_user(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> None:
        async with self._database.transaction(tenant_id) as session:
            user = await UserRepository(session, tenant_id).get_by_id(user_id)
            if user is None:
                raise NotFoundError("User not found.")
            role_repo = RoleRepository(session, tenant_id)
            role = await role_repo.get_by_id(role_id)
            if role is None:
                raise NotFoundError("Role not found.")
            await role_repo.assign_to_user(user_id, role_id, actor_id=actor_id)
        logger.info(
            "role_assigned",
            tenant_id=str(tenant_id),
            actor_id=str(actor_id),
            user_id=str(user_id),
            role_id=str(role_id),
        )

    async def revoke_role_from_user(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> None:
        async with self._database.transaction(tenant_id) as session:
            revoked = await RoleRepository(session, tenant_id).revoke_from_user(
                user_id,
                role_id,
                actor_id=actor_id,
            )
            if not revoked:
                raise NotFoundError("Role assignment not found.")
        logger.info(
            "role_revoked",
            tenant_id=str(tenant_id),
            actor_id=str(actor_id),
            user_id=str(user_id),
            role_id=str(role_id),
        )
