"""Create HR & Payroll tables (employees, payroll_runs, payroll_lines) with RLS.

Revision ID: 0011_hr_payroll
Revises: 0010_vat_mushak
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.rls import rls_disable_statements, rls_enable_statements

revision: str = "0011_hr_payroll"
down_revision: str | None = "0010_vat_mushak"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_TABLES = ("employees", "payroll_runs", "payroll_lines")


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_code", sa.String(32), nullable=False),
        sa.Column("full_name", sa.String(128), nullable=False),
        sa.Column("designation", sa.String(128), nullable=False, server_default=""),
        sa.Column("department", sa.String(128), nullable=False, server_default=""),
        sa.Column("email", sa.String(255), nullable=False, server_default=""),
        sa.Column("phone", sa.String(32), nullable=False, server_default=""),
        sa.Column("nid_no", sa.String(32), nullable=False, server_default=""),
        sa.Column("tin_no", sa.String(32), nullable=False, server_default=""),
        sa.Column("join_date", sa.Date(), nullable=False),
        sa.Column("basic_salary", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("house_rent_allowance", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("medical_allowance", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("conveyance_allowance", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("other_allowance", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("pf_deduction_percent", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("tax_deduction_amount", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("tenant_id", "employee_code", name="uq_employees_tenant_code"),
    )
    op.create_index("ix_employees_tenant_id", "employees", ["tenant_id"])
    op.create_index("ix_employees_is_deleted", "employees", ["is_deleted"])

    op.create_table(
        "payroll_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_no", sa.String(32), nullable=False),
        sa.Column("pay_year", sa.Integer(), nullable=False),
        sa.Column("pay_month", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("total_gross", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_deductions", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_net_pay", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column(
            "journal_entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("journal_entries.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("notes", sa.String(500), nullable=False, server_default=""),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("tenant_id", "run_no", name="uq_payroll_runs_tenant_no"),
        sa.UniqueConstraint("tenant_id", "pay_year", "pay_month", name="uq_payroll_runs_period"),
    )
    op.create_index("ix_payroll_runs_tenant_id", "payroll_runs", ["tenant_id"])
    op.create_index("ix_payroll_runs_is_deleted", "payroll_runs", ["is_deleted"])

    op.create_table(
        "payroll_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "payroll_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("payroll_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("employees.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("basic_salary", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("allowances_total", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("gross_salary", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("pf_deduction", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("tax_deduction", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("other_deduction", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_deductions", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("net_salary", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("payroll_run_id", "employee_id", name="uq_payroll_lines_run_emp"),
    )
    op.create_index("ix_payroll_lines_tenant_id", "payroll_lines", ["tenant_id"])
    op.create_index("ix_payroll_lines_is_deleted", "payroll_lines", ["is_deleted"])
    op.create_index("ix_payroll_lines_run_id", "payroll_lines", ["payroll_run_id"])
    op.create_index("ix_payroll_lines_employee_id", "payroll_lines", ["employee_id"])

    for table in _TENANT_TABLES:
        for statement in rls_enable_statements(table):
            op.execute(statement)


def downgrade() -> None:
    for table in reversed(_TENANT_TABLES):
        for statement in rls_disable_statements(table):
            op.execute(statement)
        op.drop_table(table)
