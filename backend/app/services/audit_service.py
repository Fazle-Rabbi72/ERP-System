"""Audit logging service and transactional helper with automatic secret redaction."""

import uuid
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Database
from app.core.exceptions import NotFoundError
from app.core.logging import REDACTED
from app.core.query import (
    FilterRule,
    PaginationParams,
    SortParams,
    build_filters,
    build_order_by,
)
from app.models.audit_log import AuditLog
from app.repositories.audit_log import AuditLogRepository

_SENSITIVE_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "otp",
)


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in _SENSITIVE_FRAGMENTS)


def _sanitise_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(k): REDACTED if _is_sensitive_key(str(k)) else _sanitise_value(v)
            for k, v in value.items()
        }
    if isinstance(value, list | tuple | set):
        return [_sanitise_value(item) for item in value]
    if isinstance(value, uuid.UUID | Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def sanitize_audit_payload(
    data: Mapping[str, object] | None,
) -> dict[str, object] | None:
    """Redact sensitive keys and convert domain types (UUID, Decimal, datetime) for JSONB."""
    if data is None:
        return None
    result = _sanitise_value(data)
    return result if isinstance(result, dict) else {}


def _current_request_id() -> str | None:
    ctx = structlog.contextvars.get_contextvars()
    req_id = ctx.get("request_id")
    return req_id if isinstance(req_id, str) else None


async def record_audit(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | uuid.UUID | None = None,
    before_data: Mapping[str, object] | None = None,
    after_data: Mapping[str, object] | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Append an audit log entry inside the caller's active database transaction."""
    repo = AuditLogRepository(session, tenant_id)
    entry = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        created_by=actor_id,
        updated_by=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        before_data=sanitize_audit_payload(before_data),
        after_data=sanitize_audit_payload(after_data),
        request_id=request_id or _current_request_id(),
        ip_address=ip_address,
    )
    return await repo.append(entry)


class AuditService:
    """Read-only query service for immutable audit logs."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def list_logs(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        action: str | None = None,
        resource_type: str | None = None,
        actor_id: uuid.UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[AuditLog], int]:
        order_by = build_order_by(
            sort,
            allowed={
                "created_at": AuditLog.created_at,
                "action": AuditLog.action,
                "resource_type": AuditLog.resource_type,
            },
            default=[AuditLog.created_at.desc(), AuditLog.id.desc()],
        )
        filters = build_filters(
            [
                FilterRule(column=AuditLog.action, operator="eq", value=action),
                FilterRule(column=AuditLog.resource_type, operator="eq", value=resource_type),
                FilterRule(column=AuditLog.actor_id, operator="eq", value=actor_id),
                FilterRule(column=AuditLog.created_at, operator="gte", value=created_from),
                FilterRule(column=AuditLog.created_at, operator="lte", value=created_to),
            ]
        )
        async with self._database.transaction(tenant_id) as session:
            return await AuditLogRepository(session, tenant_id).list_entries(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def get_log(self, *, tenant_id: uuid.UUID, entry_id: uuid.UUID) -> AuditLog:
        async with self._database.transaction(tenant_id) as session:
            entry = await AuditLogRepository(session, tenant_id).get_by_id(entry_id)
            if entry is None:
                raise NotFoundError("Audit log entry not found.")
            return entry

