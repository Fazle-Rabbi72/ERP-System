"""Create Purchase & Supplier tables (suppliers, purchase_bills, lines, payments) with RLS.

Revision ID: 0008_purchase_bills
Revises: 0007_sales_invoicing
Create Date: 2026-11-25 18:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.rls import rls_disable_statements, rls_enable_statements

revision: str = "0008_purchase_bills"
down_revision: str | None = "0007_sales_invoicing"
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
        "suppliers",
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
        sa.PrimaryKeyConstraint("id", name="pk_suppliers"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_suppliers_tenant_code"),
    )
    op.create_index("ix_suppliers_tenant_id", "suppliers", ["tenant_id"])
    op.create_index("ix_suppliers_is_deleted", "suppliers", ["is_deleted"])
    op.create_index("ix_suppliers_code", "suppliers", ["code"])

    op.create_table(
        "purchase_bills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bill_no", sa.String(length=64), nullable=False),
        sa.Column("supplier_bill_ref", sa.String(length=128), server_default="", nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expense_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bill_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("vat_total", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("gross_total", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column(
            "tds_rate_percent", sa.Numeric(5, 2), server_default=sa.text("0.00"), nullable=False
        ),
        sa.Column("tds_amount", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column(
            "vds_rate_percent", sa.Numeric(5, 2), server_default=sa.text("0.00"), nullable=False
        ),
        sa.Column("vds_amount", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("net_payable", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("paid_amount", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("notes", sa.String(length=1000), server_default="", nullable=False),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_audit_columns(),
        sa.CheckConstraint(
            "status IN ('draft', 'posted', 'partially_paid', 'paid', 'cancelled')",
            name="ck_purchase_bills_valid_bill_status",
        ),
        sa.CheckConstraint(
            "subtotal >= 0 AND vat_total >= 0 AND gross_total >= 0 "
            "AND tds_amount >= 0 AND vds_amount >= 0 AND net_payable >= 0 AND paid_amount >= 0",
            name="ck_purchase_bills_non_negative_bill_totals",
        ),
        sa.CheckConstraint(
            "paid_amount <= net_payable",
            name="ck_purchase_bills_paid_not_exceeding_net_payable",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="fk_purchase_bills_supplier_id_suppliers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["expense_account_id"],
            ["accounts.id"],
            name="fk_purchase_bills_expense_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entries.id"],
            name="fk_purchase_bills_journal_entry_id_journal_entries",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchase_bills"),
        sa.UniqueConstraint("tenant_id", "bill_no", name="uq_purchase_bills_tenant_bill_no"),
    )
    op.create_index("ix_purchase_bills_tenant_id", "purchase_bills", ["tenant_id"])
    op.create_index("ix_purchase_bills_is_deleted", "purchase_bills", ["is_deleted"])
    op.create_index("ix_purchase_bills_bill_no", "purchase_bills", ["bill_no"])
    op.create_index("ix_purchase_bills_supplier_id", "purchase_bills", ["supplier_id"])
    op.create_index("ix_purchase_bills_bill_date", "purchase_bills", ["bill_date"])
    op.create_index("ix_purchase_bills_status", "purchase_bills", ["status"])

    op.create_table(
        "purchase_bill_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "vat_rate_percent", sa.Numeric(5, 2), server_default=sa.text("0.00"), nullable=False
        ),
        sa.Column("line_subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_vat", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        *_audit_columns(),
        sa.CheckConstraint(
            "quantity > 0 AND unit_cost >= 0",
            name="ck_purchase_bill_lines_positive_qty_non_neg_cost",
        ),
        sa.CheckConstraint(
            "vat_rate_percent >= 0 AND vat_rate_percent <= 100",
            name="ck_purchase_bill_lines_valid_bill_vat_rate_range",
        ),
        sa.ForeignKeyConstraint(
            ["bill_id"],
            ["purchase_bills.id"],
            name="fk_purchase_bill_lines_bill_id_purchase_bills",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchase_bill_lines"),
    )
    op.create_index("ix_purchase_bill_lines_tenant_id", "purchase_bill_lines", ["tenant_id"])
    op.create_index("ix_purchase_bill_lines_is_deleted", "purchase_bill_lines", ["is_deleted"])
    op.create_index("ix_purchase_bill_lines_bill_id", "purchase_bill_lines", ["bill_id"])

    op.create_table(
        "supplier_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_no", sa.String(length=64), nullable=False),
        sa.Column("bill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("payment_method", sa.String(length=16), nullable=False),
        sa.Column("payment_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference", sa.String(length=128), server_default="", nullable=False),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_audit_columns(),
        sa.CheckConstraint(
            "amount > 0", name="ck_supplier_payments_positive_supplier_payment_amount"
        ),
        sa.CheckConstraint(
            "payment_method IN ('cash', 'bank', 'mfs', 'cheque')",
            name="ck_supplier_payments_valid_supplier_payment_method",
        ),
        sa.ForeignKeyConstraint(
            ["bill_id"],
            ["purchase_bills.id"],
            name="fk_supplier_payments_bill_id_purchase_bills",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="fk_supplier_payments_supplier_id_suppliers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payment_account_id"],
            ["accounts.id"],
            name="fk_supplier_payments_payment_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entries.id"],
            name="fk_supplier_payments_journal_entry_id_journal_entries",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_supplier_payments"),
        sa.UniqueConstraint(
            "tenant_id", "payment_no", name="uq_supplier_payments_tenant_payment_no"
        ),
    )
    op.create_index("ix_supplier_payments_tenant_id", "supplier_payments", ["tenant_id"])
    op.create_index("ix_supplier_payments_is_deleted", "supplier_payments", ["is_deleted"])
    op.create_index("ix_supplier_payments_payment_no", "supplier_payments", ["payment_no"])
    op.create_index("ix_supplier_payments_bill_id", "supplier_payments", ["bill_id"])
    op.create_index("ix_supplier_payments_supplier_id", "supplier_payments", ["supplier_id"])
    op.create_index("ix_supplier_payments_payment_date", "supplier_payments", ["payment_date"])

    for table in ("suppliers", "purchase_bills", "purchase_bill_lines", "supplier_payments"):
        for statement in rls_enable_statements(table):
            op.execute(statement)


def downgrade() -> None:
    for table in ("supplier_payments", "purchase_bill_lines", "purchase_bills", "suppliers"):
        for statement in rls_disable_statements(table):
            op.execute(statement)
    op.drop_table("supplier_payments")
    op.drop_table("purchase_bill_lines")
    op.drop_table("purchase_bills")
    op.drop_table("suppliers")
