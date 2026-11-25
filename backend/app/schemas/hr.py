"""Pydantic schemas for HR & Payroll."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

_TWO_PLACES = Decimal("0.01")


def _fmt_money(value: Decimal) -> str:
    return str(value.quantize(_TWO_PLACES))


class EmployeeCreateRequest(BaseModel):
    employee_code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    full_name: str = Field(min_length=2, max_length=128)
    designation: str = Field(default="", max_length=128)
    department: str = Field(default="", max_length=128)
    email: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=32)
    nid_no: str = Field(default="", max_length=32)
    tin_no: str = Field(default="", max_length=32)
    join_date: date
    basic_salary: Decimal = Field(gt=Decimal("0.00"), decimal_places=2)
    house_rent_allowance: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2
    )
    medical_allowance: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2
    )
    conveyance_allowance: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2
    )
    other_allowance: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2)
    pf_deduction_percent: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("50.00"), decimal_places=2
    )
    tax_deduction_amount: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2
    )


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_code: str
    full_name: str
    designation: str
    department: str
    email: str
    phone: str
    nid_no: str
    tin_no: str
    join_date: date
    basic_salary: Decimal
    house_rent_allowance: Decimal
    medical_allowance: Decimal
    conveyance_allowance: Decimal
    other_allowance: Decimal
    pf_deduction_percent: Decimal
    tax_deduction_amount: Decimal
    is_active: bool
    created_at: datetime

    @field_serializer(
        "basic_salary",
        "house_rent_allowance",
        "medical_allowance",
        "conveyance_allowance",
        "other_allowance",
        "pf_deduction_percent",
        "tax_deduction_amount",
    )
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class PayrollRunCreateRequest(BaseModel):
    pay_year: int = Field(ge=2020, le=2100)
    pay_month: int = Field(ge=1, le=12)
    notes: str = Field(default="", max_length=500)


class PayrollRunPostRequest(BaseModel):
    salary_expense_account_id: uuid.UUID
    payment_account_id: uuid.UUID
    deductions_payable_account_id: uuid.UUID | None = None


class PayrollLineResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    employee_code: str
    employee_name: str
    designation: str
    basic_salary: Decimal
    allowances_total: Decimal
    gross_salary: Decimal
    pf_deduction: Decimal
    tax_deduction: Decimal
    other_deduction: Decimal
    total_deductions: Decimal
    net_salary: Decimal

    @field_serializer(
        "basic_salary",
        "allowances_total",
        "gross_salary",
        "pf_deduction",
        "tax_deduction",
        "other_deduction",
        "total_deductions",
        "net_salary",
    )
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class PayrollRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_no: str
    pay_year: int
    pay_month: int
    status: str
    total_gross: Decimal
    total_deductions: Decimal
    total_net_pay: Decimal
    journal_entry_id: uuid.UUID | None
    notes: str
    posted_at: datetime | None
    created_at: datetime

    @field_serializer("total_gross", "total_deductions", "total_net_pay")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class PayrollRunDetailResponse(PayrollRunResponse):
    lines: list[PayrollLineResponse]
    advisory_note: str
