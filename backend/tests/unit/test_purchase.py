"""Unit tests for exact Decimal purchase bill VAT, TDS & VDS calculations."""

from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError
from app.schemas.purchase import PurchaseBillLineCreateRequest
from app.services.purchase_service import compute_bill_totals

pytestmark = pytest.mark.unit


def test_compute_bill_totals_with_configurable_vat_tds_and_vds() -> None:
    lines = [
        PurchaseBillLineCreateRequest(
            description="IT Consulting Service",
            quantity=Decimal("1"),
            unit_cost=Decimal("100000.00"),
            vat_rate_percent=Decimal("15.00"),
        )
    ]
    totals = compute_bill_totals(
        lines,
        tds_rate_percent=Decimal("5.00"),
        vds_rate_percent=Decimal("7.50"),
    )
    assert totals.subtotal == Decimal("100000.00")
    assert totals.vat_total == Decimal("15000.00")
    assert totals.gross_total == Decimal("115000.00")
    assert totals.tds_amount == Decimal("5000.00")
    assert totals.vds_amount == Decimal("7500.00")
    assert totals.net_payable == Decimal("102500.00")
    # Accounting invariant: gross_total == net_payable + tds + vds
    assert totals.gross_total == totals.net_payable + totals.tds_amount + totals.vds_amount


def test_compute_bill_totals_rejects_non_positive_net_payable() -> None:
    lines = [
        PurchaseBillLineCreateRequest(
            description="Item",
            quantity=Decimal("1"),
            unit_cost=Decimal("100.00"),
        )
    ]
    with pytest.raises(BusinessRuleError):
        compute_bill_totals(
            lines,
            tds_rate_percent=Decimal("60.00"),
            vds_rate_percent=Decimal("50.00"),
        )
