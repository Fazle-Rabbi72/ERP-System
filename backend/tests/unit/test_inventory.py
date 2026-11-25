"""Unit tests for Inventory quantity sign normalization and valuation."""

from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError
from app.services.inventory_service import compute_stock_value, normalize_signed_quantity

pytestmark = pytest.mark.unit


def test_normalize_signed_quantity() -> None:
    assert normalize_signed_quantity("in", Decimal("15.500")) == Decimal("15.500")
    assert normalize_signed_quantity("out", Decimal("4.000")) == Decimal("-4.000")
    assert normalize_signed_quantity("adjustment", Decimal("-2.250")) == Decimal("-2.250")

    with pytest.raises(BusinessRuleError):
        normalize_signed_quantity("in", Decimal("0.000"))
    with pytest.raises(BusinessRuleError):
        normalize_signed_quantity("out", Decimal("-5.000"))


def test_compute_stock_value_exact_decimal() -> None:
    assert compute_stock_value(Decimal("12.500"), Decimal("1250.33")) == Decimal("15629.13")
