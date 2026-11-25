"""HR & Payroll models: Employee, PayrollRun, PayrollLine.

All allowance, PF, and income-tax deduction values are tenant-configurable;
no statutory Bangladesh Labour Act / NBR tax slabs are hardcoded.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MONEY_TYPE, TenantBaseModel

RATE_TYPE = Numeric(5, 2)


class Employee(TenantBaseModel):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_code", name="uq_employees_tenant_code"),
    )

    employee_code: Mapped[str] = mapped_column(String(32), nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    designation: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    department: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    nid_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    tin_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    join_date: Mapped[date] = mapped_column(Date, nullable=False)

    basic_salary: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False, default=Decimal("0"))
    house_rent_allowance: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0")
    )
    medical_allowance: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0")
    )
    conveyance_allowance: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0")
    )
    other_allowance: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0")
    )
    pf_deduction_percent: Mapped[Decimal] = mapped_column(
        RATE_TYPE, nullable=False, default=Decimal("0")
    )
    tax_deduction_amount: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PayrollRun(TenantBaseModel):
    __tablename__ = "payroll_runs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "run_no", name="uq_payroll_runs_tenant_no"),
        UniqueConstraint("tenant_id", "pay_year", "pay_month", name="uq_payroll_runs_period"),
    )

    run_no: Mapped[str] = mapped_column(String(32), nullable=False)
    pay_year: Mapped[int] = mapped_column(Integer, nullable=False)
    pay_month: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    total_gross: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False, default=Decimal("0"))
    total_deductions: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0")
    )
    total_net_pay: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False, default=Decimal("0"))
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="RESTRICT"),
        nullable=True,
    )
    notes: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)


class PayrollLine(TenantBaseModel):
    __tablename__ = "payroll_lines"
    __table_args__ = (
        UniqueConstraint("payroll_run_id", "employee_id", name="uq_payroll_lines_run_emp"),
    )

    payroll_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payroll_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    basic_salary: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False, default=Decimal("0"))
    allowances_total: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0")
    )
    gross_salary: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False, default=Decimal("0"))
    pf_deduction: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False, default=Decimal("0"))
    tax_deduction: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False, default=Decimal("0"))
    other_deduction: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0")
    )
    total_deductions: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0")
    )
    net_salary: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False, default=Decimal("0"))
