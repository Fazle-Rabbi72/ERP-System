"""Declarative base and mandatory columns for every Nexzen ERP table.

Every table MUST inherit from `TenantBaseModel` so that:
- Primary key is a UUID (`id`).
- Multi-tenant isolation (`tenant_id`) is universal and enforceable by RLS.
- Audit timestamps and actor ids (`created_at`, `updated_at`, `created_by`, `updated_by`) exist.
- Deletions are soft (`is_deleted`) rather than destructive.
- Money columns use `MONEY_TYPE` (`NUMERIC(18, 2)` -> Python `Decimal`, never `float`).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, MetaData, Numeric, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Standard BDT / currency column type: NUMERIC(18, 2), always mapped to Decimal.
MONEY_TYPE = Numeric(18, 2, asdecimal=True)


class Base(DeclarativeBase):
    """Shared declarative base with deterministic constraint names for Alembic."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TenantBaseModel(Base):
    """Abstract base for all tenant-scoped tables."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
    )
