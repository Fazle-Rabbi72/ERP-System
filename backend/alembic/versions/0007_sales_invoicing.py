"""Create Sales & Invoicing tables (customers, sales_invoices, lines, payments) with RLS.

Revision ID: 0007_sales_invoicing
Revises: 0006_accounting_gl
Create Date: 2026-11-25 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.rls import rls_disable_statements, rls_enable_statements

revision: str = "0007_sales_invoicing"
down_revision: str | None = "0006_accounting_gl"
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
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), server_default="", nullable=False),
        sa.Column("email", sa.String(length=255), server_default="", nullable=False),
        sa.Column("address", sa.String(length=500), server_default="", nullable=False),
        sa.Column("bin_no", sa.String(length=32), server_default="", nullable=False),
        sa.Column("tin_no", sa.String(length=32), server_default="", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_customers_tenant_code"),
    )
    op.create_index("ix_customers_tenant_id", "customers", ["tenant_id"])
    op.create_index("ix_customers_is_deleted", "customers", ["is_deleted"])
    op.create_index("ix_customers_code", "customers", ["code"])

    op.create_table(
        "sales_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_no", sa.String(length=64), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("vat_total", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("grand_total", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("paid_amount", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("notes", sa.String(length=1000), server_default="", nullable=False),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_audit_columns(),
        sa.CheckConstraint(
            "status IN ('draft', 'posted', 'partially_paid', 'paid', 'cancelled')",
            name="ck_sales_invoices_valid_invoice_status",
        ),
        sa.CheckConstraint(
            "subtotal >= 0 AND vat_total >= 0 AND grand_total >= 0 AND paid_amount >= 0",
            name="ck_sales_invoices_non_negative_totals",
        ),
        sa.CheckConstraint(
            "paid_amount <= grand_total",
            name="ck_sales_invoices_paid_not_exceeding_total",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_sales_invoices_customer_id_customers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entries.id"],
            name="fk_sales_invoices_journal_entry_id_journal_entries",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sales_invoices"),
        sa.UniqueConstraint("tenant_id", "invoice_no", name="uq_sales_invoices_tenant_invoice_no"),
    )
    op.create_index("ix_sales_invoices_tenant_id", "sales_invoices", ["tenant_id"])
    op.create_index("ix_sales_invoices_is_deleted", "sales_invoices", ["is_deleted"])
    op.create_index("ix_sales_invoices_invoice_no", "sales_invoices", ["invoice_no"])
    op.create_index("ix_sales_invoices_customer_id", "sales_invoices", ["customer_id"])
    op.create_index("ix_sales_invoices_invoice_date", "sales_invoices", ["invoice_date"])
    op.create_index("ix_sales_invoices_status", "sales_invoices", ["status"])

    op.create_table(
        "sales_invoice_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "vat_rate_percent", sa.Numeric(5, 2), server_default=sa.text("0.00"), nullable=False
        ),
        sa.Column("line_subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_vat", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        *_audit_columns(),
        sa.CheckConstraint(
            "quantity > 0 AND unit_price >= 0",
            name="ck_sales_invoice_lines_positive_qty_non_neg_price",
        ),
        sa.CheckConstraint(
            "vat_rate_percent >= 0 AND vat_rate_percent <= 100",
            name="ck_sales_invoice_lines_valid_vat_rate_range",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["sales_invoices.id"],
            name="fk_sales_invoice_lines_invoice_id_sales_invoices",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sales_invoice_lines"),
    )
    op.create_index("ix_sales_invoice_lines_tenant_id", "sales_invoice_lines", ["tenant_id"])
    op.create_index("ix_sales_invoice_lines_is_deleted", "sales_invoice_lines", ["is_deleted"])
    op.create_index("ix_sales_invoice_lines_invoice_id", "sales_invoice_lines", ["invoice_id"])

    op.create_table(
        "customer_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_no", sa.String(length=64), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("payment_method", sa.String(length=16), nullable=False),
        sa.Column("deposit_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference", sa.String(length=128), server_default="", nullable=False),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_audit_columns(),
        sa.CheckConstraint("amount > 0", name="ck_customer_payments_positive_payment_amount"),
        sa.CheckConstraint(
            "payment_method IN ('cash', 'bank', 'mfs', 'cheque')",
            name="ck_customer_payments_valid_payment_method",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["sales_invoices.id"],
            name="fk_customer_payments_invoice_id_sales_invoices",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_customer_payments_customer_id_customers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["deposit_account_id"],
            ["accounts.id"],
            name="fk_customer_payments_deposit_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entries.id"],
            name="fk_customer_payments_journal_entry_id_journal_entries",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_customer_payments"),
        sa.UniqueConstraint(
            "tenant_id", "payment_no", name="uq_customer_payments_tenant_payment_no"
        ),
    )
    op.create_index("ix_customer_payments_tenant_id", "customer_payments", ["tenant_id"])
    op.create_index("ix_customer_payments_is_deleted", "customer_payments", ["is_deleted"])
    op.create_index("ix_customer_payments_payment_no", "customer_payments", ["payment_no"])
    op.create_index("ix_customer_payments_invoice_id", "customer_payments", ["invoice_id"])
    op.create_index("ix_customer_payments_customer_id", "customer_payments", ["customer_id"])
    op.create_index("ix_customer_payments_payment_date", "customer_payments", ["payment_date"])

    for table in ("customers", "sales_invoices", "sales_invoice_lines", "customer_payments"):
        for statement in rls_enable_statements(table):
            op.execute(statement)


def downgrade() -> None:
    for table in ("customer_payments", "sales_invoice_lines", "sales_invoices", "customers"):
        for statement in rls_disable_statements(table):
            op.execute(statement)
    op.drop_table("customer_payments")
    op.drop_table("sales_invoice_lines")
    op.drop_table("sales_invoices")
    op.drop_table("customers")
