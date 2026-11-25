"""Create Accounting & GL tables (accounts, journal_entries, journal_lines) with RLS.

Revision ID: 0006_accounting_gl
Revises: 0005_widen_audit_resource_id
Create Date: 2026-11-25 17:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.rls import rls_disable_statements, rls_enable_statements

revision: str = "0006_accounting_gl"
down_revision: str | None = "0005_widen_audit_resource_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _audit_columns() -> list[sa.Column[object]]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=16), nullable=False),
        sa.Column("normal_balance", sa.String(length=8), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_group", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("description", sa.String(length=500), server_default="", nullable=False),
        *_audit_columns(),
        sa.CheckConstraint(
            "account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')",
            name="ck_accounts_valid_account_type",
        ),
        sa.CheckConstraint(
            "normal_balance IN ('debit', 'credit')",
            name="ck_accounts_valid_normal_balance",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["accounts.id"],
            name="fk_accounts_parent_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_accounts_tenant_code"),
    )
    op.create_index("ix_accounts_tenant_id", "accounts", ["tenant_id"])
    op.create_index("ix_accounts_is_deleted", "accounts", ["is_deleted"])
    op.create_index("ix_accounts_code", "accounts", ["code"])
    op.create_index("ix_accounts_account_type", "accounts", ["account_type"])
    op.create_index("ix_accounts_parent_id", "accounts", ["parent_id"])

    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voucher_no", sa.String(length=64), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("reference", sa.String(length=128), server_default="", nullable=False),
        sa.Column("narration", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reversed_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_audit_columns(),
        sa.CheckConstraint(
            "status IN ('draft', 'posted', 'reversed')",
            name="ck_journal_entries_valid_journal_status",
        ),
        sa.ForeignKeyConstraint(
            ["reversed_entry_id"],
            ["journal_entries.id"],
            name="fk_journal_entries_reversed_entry_id_journal_entries",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_journal_entries"),
        sa.UniqueConstraint("tenant_id", "voucher_no", name="uq_journal_entries_tenant_voucher_no"),
    )
    op.create_index("ix_journal_entries_tenant_id", "journal_entries", ["tenant_id"])
    op.create_index("ix_journal_entries_is_deleted", "journal_entries", ["is_deleted"])
    op.create_index("ix_journal_entries_voucher_no", "journal_entries", ["voucher_no"])
    op.create_index("ix_journal_entries_entry_date", "journal_entries", ["entry_date"])
    op.create_index("ix_journal_entries_status", "journal_entries", ["status"])

    op.create_table(
        "journal_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=500), server_default="", nullable=False),
        sa.Column("debit", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("credit", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        *_audit_columns(),
        sa.CheckConstraint(
            "debit >= 0 AND credit >= 0", name="ck_journal_lines_non_negative_amounts"
        ),
        sa.CheckConstraint(
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
            name="ck_journal_lines_exclusive_debit_or_credit",
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entries.id"],
            name="fk_journal_lines_journal_entry_id_journal_entries",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_journal_lines_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_journal_lines"),
    )
    op.create_index("ix_journal_lines_tenant_id", "journal_lines", ["tenant_id"])
    op.create_index("ix_journal_lines_is_deleted", "journal_lines", ["is_deleted"])
    op.create_index("ix_journal_lines_journal_entry_id", "journal_lines", ["journal_entry_id"])
    op.create_index("ix_journal_lines_account_id", "journal_lines", ["account_id"])

    for table in ("accounts", "journal_entries", "journal_lines"):
        for statement in rls_enable_statements(table):
            op.execute(statement)


def downgrade() -> None:
    for table in ("journal_lines", "journal_entries", "accounts"):
        for statement in rls_disable_statements(table):
            op.execute(statement)
    op.drop_table("journal_lines")
    op.drop_table("journal_entries")
    op.drop_table("accounts")
