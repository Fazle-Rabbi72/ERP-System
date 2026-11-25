"""Unit tests for exact Decimal sales line and configurable VAT calculations."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.sales import InvoiceLineCreateRequest, SalesInvoiceCreateRequest
from app.services.sales_service import compute_line_totals

pytestmark = pytest.mark.unit


def test_compute_line_totals_exact_decimal_with_configurable_vat() -> None:
    line = InvoiceLineCreateRequest(
        description="ERP Annual License",
        quantity=Decimal("3"),
        unit_price=Decimal("33333.33"),
        vat_rate_percent=Decimal("15.00"),
    )
    computed = compute_line_totals(line)
    assert computed.line_subtotal == Decimal("99999.99")
    assert computed.line_vat == Decimal("15000.00")
    assert computed.line_total == Decimal("114999.99")


def test_compute_line_totals_zero_vat_default() -> None:
    line = InvoiceLineCreateRequest(
        description="Exempted Export Service",
        quantity=Decimal("2.500"),
        unit_price=Decimal("1000.00"),
    )
    computed = compute_line_totals(line)
    assert computed.vat_rate_percent == Decimal("0.00")
    assert computed.line_subtotal == Decimal("2500.00")
    assert computed.line_vat == Decimal("0.00")
    assert computed.line_total == Decimal("2500.00")


def test_invoice_rejects_due_date_before_invoice_date() -> None:
    with pytest.raises(ValidationError, match="due_date"):
        SalesInvoiceCreateRequest(
            customer_id=uuid.uuid4(),
            invoice_date=date(2026, 11, 25),
            due_date=date(2026, 11, 20),
            lines=[
                InvoiceLineCreateRequest(
                    description="Item",
                    quantity=Decimal("1"),
                    unit_price=Decimal("100.00"),
                )
            ],
        )
