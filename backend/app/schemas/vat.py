"""Pydantic schemas for configurable VAT rates and Mushak 6.1, 6.2, 6.3, 9.1 reports."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

_TWO_PLACES = Decimal("0.01")


def _fmt_money(value: Decimal) -> str:
    return str(value.quantize(_TWO_PLACES))


class VatRateCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=128)
    rate_percent: Decimal = Field(ge=Decimal("0.00"), le=Decimal("100.00"), decimal_places=2)
    is_vds_applicable: bool = False
    statutory_note: str = Field(default="", max_length=500)


class VatRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    rate_percent: Decimal
    is_vds_applicable: bool
    statutory_note: str
    is_active: bool
    created_at: datetime

    @field_serializer("rate_percent")
    def _serialize_rate(self, value: Decimal) -> str:
        return _fmt_money(value)


class Mushak61ItemResponse(BaseModel):
    bill_id: uuid.UUID
    bill_no: str
    bill_date: date
    supplier_bill_ref: str
    supplier_name: str
    supplier_bin: str
    taxable_value: Decimal
    input_vat: Decimal
    vds_amount: Decimal
    tds_amount: Decimal
    gross_total: Decimal

    @field_serializer("taxable_value", "input_vat", "vds_amount", "tds_amount", "gross_total")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class Mushak61ReportResponse(BaseModel):
    date_from: date | None
    date_to: date | None
    items: list[Mushak61ItemResponse]
    total_taxable_value: Decimal
    total_input_vat: Decimal
    total_vds: Decimal
    total_tds: Decimal

    @field_serializer("total_taxable_value", "total_input_vat", "total_vds", "total_tds")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class Mushak62ItemResponse(BaseModel):
    invoice_id: uuid.UUID
    invoice_no: str
    invoice_date: date
    customer_name: str
    customer_bin: str
    taxable_value: Decimal
    output_vat: Decimal
    grand_total: Decimal

    @field_serializer("taxable_value", "output_vat", "grand_total")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class Mushak62ReportResponse(BaseModel):
    date_from: date | None
    date_to: date | None
    items: list[Mushak62ItemResponse]
    total_taxable_value: Decimal
    total_output_vat: Decimal
    total_grand_total: Decimal

    @field_serializer("total_taxable_value", "total_output_vat", "total_grand_total")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class Mushak63LineResponse(BaseModel):
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


class Mushak63ChallanResponse(BaseModel):
    invoice_id: uuid.UUID
    invoice_no: str
    invoice_date: date
    seller_name: str
    customer_name: str
    customer_bin: str
    customer_address: str
    lines: list[Mushak63LineResponse]
    subtotal: Decimal
    vat_total: Decimal
    grand_total: Decimal

    @field_serializer("subtotal", "vat_total", "grand_total")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class Mushak91SummaryResponse(BaseModel):
    date_from: date | None
    date_to: date | None
    total_sales_taxable: Decimal
    total_output_vat: Decimal
    total_purchase_taxable: Decimal
    total_input_vat: Decimal
    net_vat_payable: Decimal
    carry_forward_credit: Decimal
    total_vds_payable: Decimal
    total_tds_payable: Decimal
    advisory_note: str

    @field_serializer(
        "total_sales_taxable",
        "total_output_vat",
        "total_purchase_taxable",
        "total_input_vat",
        "net_vat_payable",
        "carry_forward_credit",
        "total_vds_payable",
        "total_tds_payable",
    )
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)
