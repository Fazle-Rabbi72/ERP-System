"""RBAC HTTP router: roles, permissions, and user-role assignments."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_auth, get_rbac_service, require_permission
from app.core.permissions import (
    PERM_RBAC_ROLES_READ,
    PERM_RBAC_ROLES_WRITE,
    PERM_RBAC_USERS_ASSIGN,
)
from app.core.query import PaginationParams, SortParams, get_pagination_params, get_sort_params
from app.core.security import TokenPayload
from app.schemas.common import PaginatedResponse
from app.schemas.rbac import (
    EffectivePermissionsResponse,
    PermissionResponse,
    RoleCreateRequest,
    RoleResponse,
)
from app.services.rbac_service import RbacService

router = APIRouter(prefix="/rbac", tags=["rbac"])


@router.get("/me/permissions", response_model=EffectivePermissionsResponse)
async def my_permissions(
    auth: Annotated[TokenPayload, Depends(get_current_auth)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> EffectivePermissionsResponse:
    perms = await service.get_user_permissions(auth.tenant_id, auth.sub)
    return EffectivePermissionsResponse(
        user_id=auth.sub,
        tenant_id=auth.tenant_id,
        permissions=sorted(perms),
    )


@router.get("/roles", response_model=PaginatedResponse[RoleResponse])
async def list_roles(
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_RBAC_ROLES_READ))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    search: Annotated[str | None, Query(max_length=128)] = None,
) -> PaginatedResponse[RoleResponse]:
    items, total = await service.list_roles(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        search=search,
    )
    return PaginatedResponse[RoleResponse].create(
        items=[RoleResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    body: RoleCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_RBAC_ROLES_WRITE))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> RoleResponse:
    role = await service.create_role(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        code=body.code,
        name=body.name,
        description=body.description,
        permission_codes=body.permission_codes,
    )
    return RoleResponse.model_validate(role)


@router.get("/permissions", response_model=PaginatedResponse[PermissionResponse])
async def list_permissions(
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_RBAC_ROLES_READ))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    module: Annotated[str | None, Query(max_length=64)] = None,
) -> PaginatedResponse[PermissionResponse]:
    items, total = await service.list_permissions(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        module=module,
    )
    return PaginatedResponse[PermissionResponse].create(
        items=[PermissionResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/users/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def assign_role(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_RBAC_USERS_ASSIGN))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> None:
    await service.assign_role_to_user(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        user_id=user_id,
        role_id=role_id,
    )


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_role(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_RBAC_USERS_ASSIGN))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> None:
    await service.revoke_role_from_user(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        user_id=user_id,
        role_id=role_id,
    )
