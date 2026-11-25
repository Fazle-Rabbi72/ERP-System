"""Immutable append-only audit log model (tenant-scoped, protected by DB trigger + RLS)."""

import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBaseModel


class AuditLog(TenantBaseModel):
    """Append-only record of who did what, when, and what changed.

    A PostgreSQL BEFORE UPDATE OR DELETE trigger enforces immutability at the
    database layer so records cannot be altered or erased.
    """

    __tablename__ = "audit_logs"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    before_data: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    after_data: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
