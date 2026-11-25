"""Pydantic schemas for Purchase & Supplier (configurable VAT, TDS, VDS)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

BillStatus = Literal["draft", "posted", "partially_paid", "paid", "cancelled"]
PaymentMethod = Literal["cash", "bank", "mfs", "cheque"]

_TWO_PLACES = Decimal("0.01")


def _fmt_money(value: Decimal) -> str:
    return str(value.quantize(_TWO_PLACES))


class SupplierCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    phone: str = Field(default="", max_length=32)
    email: str = Field(default="", max_length=255)
    address: str = Field(default="", max_length=500)
    bin_no: str = Field(default="", max_length=32)
    tin_no: str = Field(default="", max_length=32)


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    phone: str
    email: str
    address: str
    bin_no: str
    tin_no: str
    is_active: bool
    created_at: datetime


class PurchaseBillLineCreateRequest(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=Decimal("0"), decimal_places=3)
    unit_cost: Decimal = Field(ge=Decimal("0.00"), decimal_places=2)
    vat_rate_percent: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        decimal_places=2,
    )


class PurchaseBillCreateRequest(BaseModel):
    supplier_id: uuid.UUID
    expense_account_id: uuid.UUID
    supplier_bill_ref: str = Field(default="", max_length=128)
    bill_date: date
    due_date: date
    tds_rate_percent: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        decimal_places=2,
        description="Configurable TDS rate percentage on subtotal (never hardcoded).",
    )
    vds_rate_percent: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        decimal_places=2,
        description="Configurable VDS rate percentage on subtotal (never hardcoded).",
    )
    notes: str = Field(default="", max_length=1000)
    lines: list[PurchaseBillLineCreateRequest] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_dates(self) -> "PurchaseBillCreateRequest":
        if self.due_date < self.bill_date:
            msg = "due_date cannot be earlier than bill_date."
            raise ValueError(msg)
        return self


class PurchaseBillLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    line_no: int
    description: str
    quantity: Decimal
    unit_cost: Decimal
    vat_rate_percent: Decimal
    line_subtotal: Decimal
    line_vat: Decimal
    line_total: Decimal

    @field_serializer("unit_cost", "vat_rate_percent", "line_subtotal", "line_vat", "line_total")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)

    @field_serializer("quantity")
    def _serialize_qty(self, value: Decimal) -> str:
        return str(value)


class PurchaseBillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bill_no: str
    supplier_bill_ref: str
    supplier_id: uuid.UUID
    expense_account_id: uuid.UUID
    bill_date: date
    due_date: date
    status: BillStatus
    subtotal: Decimal
    vat_total: Decimal
    gross_total: Decimal
    tds_rate_percent: Decimal
    tds_amount: Decimal
    vds_rate_percent: Decimal
    vds_amount: Decimal
    net_payable: Decimal
    paid_amount: Decimal
    notes: str
    journal_entry_id: uuid.UUID | None
    lines: list[PurchaseBillLineResponse]
    created_at: datetime

    @field_serializer(
        "subtotal",
        "vat_total",
        "gross_total",
        "tds_rate_percent",
        "tds_amount",
        "vds_rate_percent",
        "vds_amount",
        "net_payable",
        "paid_amount",
    )
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class SupplierPaymentCreateRequest(BaseModel):
    payment_date: date
    amount: Decimal = Field(gt=Decimal("0.00"), decimal_places=2)
    payment_method: PaymentMethod = "bank"
    payment_account_id: uuid.UUID
    reference: str = Field(default="", max_length=128)


class SupplierPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payment_no: str
    bill_id: uuid.UUID
    supplier_id: uuid.UUID
    payment_date: date
    amount: Decimal
    payment_method: PaymentMethod
    payment_account_id: uuid.UUID
    reference: str
    journal_entry_id: uuid.UUID | None
    created_at: datetime

    @field_serializer("amount")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)
