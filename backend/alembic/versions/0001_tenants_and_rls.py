"""Create tenants table with standard audit/soft-delete columns and RLS policy.

Revision ID: 0001_tenants_and_rls
Revises:
Create Date: 2026-11-25 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.rls import rls_disable_statements, rls_enable_statements

revision: str = "0001_tenants_and_rls"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint("tenant_id = id", name="ck_tenants_self_tenant_id"),
        sa.PrimaryKeyConstraint("id", name="pk_tenants"),
        sa.UniqueConstraint("code", name="uq_tenants_code"),
    )
    op.create_index("ix_tenants_tenant_id", "tenants", ["tenant_id"], unique=False)
    op.create_index("ix_tenants_is_deleted", "tenants", ["is_deleted"], unique=False)
    op.create_index("ix_tenants_code", "tenants", ["code"], unique=True)

    for statement in rls_enable_statements("tenants"):
        op.execute(statement)


def downgrade() -> None:
    for statement in rls_disable_statements("tenants"):
        op.execute(statement)
    op.drop_index("ix_tenants_code", table_name="tenants")
    op.drop_index("ix_tenants_is_deleted", table_name="tenants")
    op.drop_index("ix_tenants_tenant_id", table_name="tenants")
    op.drop_table("tenants")
