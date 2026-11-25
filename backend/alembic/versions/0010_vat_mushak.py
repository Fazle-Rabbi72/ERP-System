"""Create configurable vat_rates table with RLS.

Revision ID: 0010_vat_mushak
Revises: 0009_inventory_warehouse
Create Date: 2026-11-25 19:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.rls import rls_disable_statements, rls_enable_statements

revision: str = "0010_vat_mushak"
down_revision: str | None = "0009_inventory_warehouse"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vat_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("rate_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "is_vds_applicable", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("statutory_note", sa.String(length=500), server_default="", nullable=False),
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
        sa.CheckConstraint(
            "rate_percent >= 0 AND rate_percent <= 100", name="ck_vat_rates_valid_vat_rate_pct"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vat_rates"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_vat_rates_tenant_code"),
    )
    op.create_index("ix_vat_rates_tenant_id", "vat_rates", ["tenant_id"])
    op.create_index("ix_vat_rates_is_deleted", "vat_rates", ["is_deleted"])
    op.create_index("ix_vat_rates_code", "vat_rates", ["code"])

    for statement in rls_enable_statements("vat_rates"):
        op.execute(statement)


def downgrade() -> None:
    for statement in rls_disable_statements("vat_rates"):
        op.execute(statement)
    op.drop_table("vat_rates")
