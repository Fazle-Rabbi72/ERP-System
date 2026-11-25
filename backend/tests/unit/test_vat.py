"""Unit tests for Mushak 9.1 net VAT payable vs carry-forward credit math."""

from decimal import Decimal

import pytest

from app.services.vat_service import compute_net_vat_position

pytestmark = pytest.mark.unit


def test_compute_net_vat_position_payable_and_credit() -> None:
    payable, credit = compute_net_vat_position(Decimal("45000.50"), Decimal("30000.25"))
    assert payable == Decimal("15000.25")
    assert credit == Decimal("0.00")

    payable2, credit2 = compute_net_vat_position(Decimal("10000.00"), Decimal("25000.75"))
    assert payable2 == Decimal("0.00")
    assert credit2 == Decimal("15000.75")
