"""Widen audit_logs.resource_id to VARCHAR(128) for composite resource keys (e.g. user:role).

Revision ID: 0005_widen_audit_resource_id
Revises: 0004_audit_logs_immutable
Create Date: 2026-11-25 17:18:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_widen_audit_resource_id"
down_revision: str | None = "0004_audit_logs_immutable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "audit_logs",
        "resource_id",
        existing_type=sa.String(length=64),
        type_=sa.String(length=128),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "audit_logs",
        "resource_id",
        existing_type=sa.String(length=128),
        type_=sa.String(length=64),
        existing_nullable=True,
    )
