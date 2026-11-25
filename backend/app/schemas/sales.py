"""Pydantic schemas for Sales & Invoicing.

All money values are `Decimal` serialized as exact 2-decimal strings.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

InvoiceStatus = Literal["draft", "posted", "partially_paid", "paid", "cancelled"]
PaymentMethod = Literal["cash", "bank", "mfs", "cheque"]

_TWO_PLACES = Decimal("0.01")


def _fmt_money(value: Decimal) -> str:
    return str(value.quantize(_TWO_PLACES))


class CustomerCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    phone: str = Field(default="", max_length=32)
    email: str = Field(default="", max_length=255)
    address: str = Field(default="", max_length=500)
    bin_no: str = Field(default="", max_length=32, description="Optional 13-digit Bangladesh BIN")
    tin_no: str = Field(default="", max_length=32, description="Optional TIN")


class CustomerResponse(BaseModel):
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


class InvoiceLineCreateRequest(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=Decimal("0"), decimal_places=3)
    unit_price: Decimal = Field(ge=Decimal("0.00"), decimal_places=2)
    vat_rate_percent: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        decimal_places=2,
        description="Configurable VAT rate percentage (never hardcoded).",
    )


class SalesInvoiceCreateRequest(BaseModel):
    customer_id: uuid.UUID
    invoice_date: date
    due_date: date
    notes: str = Field(default="", max_length=1000)
    lines: list[InvoiceLineCreateRequest] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_dates(self) -> "SalesInvoiceCreateRequest":
        if self.due_date < self.invoice_date:
            msg = "due_date cannot be earlier than invoice_date."
            raise ValueError(msg)
        return self


class InvoiceLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    line_no: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_rate_percent: Decimal
    line_subtotal: Decimal
    line_vat: Decimal
    line_total: Decimal

    @field_serializer("unit_price", "vat_rate_percent", "line_subtotal", "line_vat", "line_total")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)

    @field_serializer("quantity")
    def _serialize_qty(self, value: Decimal) -> str:
        return str(value)


class SalesInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_no: str
    customer_id: uuid.UUID
    invoice_date: date
    due_date: date
    status: InvoiceStatus
    subtotal: Decimal
    vat_total: Decimal
    grand_total: Decimal
    paid_amount: Decimal
    notes: str
    journal_entry_id: uuid.UUID | None
    lines: list[InvoiceLineResponse]
    created_at: datetime

    @field_serializer("subtotal", "vat_total", "grand_total", "paid_amount")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class CustomerPaymentCreateRequest(BaseModel):
    payment_date: date
    amount: Decimal = Field(gt=Decimal("0.00"), decimal_places=2)
    payment_method: PaymentMethod = "cash"
    deposit_account_id: uuid.UUID
    reference: str = Field(default="", max_length=128)


class CustomerPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payment_no: str
    invoice_id: uuid.UUID
    customer_id: uuid.UUID
    payment_date: date
    amount: Decimal
    payment_method: PaymentMethod
    deposit_account_id: uuid.UUID
    reference: str
    journal_entry_id: uuid.UUID | None
    created_at: datetime

    @field_serializer("amount")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)
