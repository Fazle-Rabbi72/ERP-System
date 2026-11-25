"""Read-only HTTP router for immutable audit logs."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_audit_service, require_permission
from app.core.permissions import PERM_AUDIT_READ
from app.core.query import PaginationParams, SortParams, get_pagination_params, get_sort_params
from app.core.security import TokenPayload
from app.schemas.audit import AuditLogResponse
from app.schemas.common import PaginatedResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_AUDIT_READ))],
    service: Annotated[AuditService, Depends(get_audit_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    action: Annotated[str | None, Query(max_length=128)] = None,
    resource_type: Annotated[str | None, Query(max_length=64)] = None,
    actor_id: Annotated[uuid.UUID | None, Query()] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
) -> PaginatedResponse[AuditLogResponse]:
    items, total = await service.list_logs(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        action=action,
        resource_type=resource_type,
        actor_id=actor_id,
        created_from=created_from,
        created_to=created_to,
    )
    return PaginatedResponse[AuditLogResponse].create(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{entry_id}", response_model=AuditLogResponse)
async def get_audit_log(
    entry_id: uuid.UUID,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_AUDIT_READ))],
    service: Annotated[AuditService, Depends(get_audit_service)],
) -> AuditLogResponse:
    entry = await service.get_log(tenant_id=auth.tenant_id, entry_id=entry_id)
    return AuditLogResponse.model_validate(entry)
