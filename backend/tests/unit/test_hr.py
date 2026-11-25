"""Unit tests for HR & Payroll pure calculation logic."""

from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError
from app.services.hr_service import compute_payslip


def test_compute_payslip_exact_decimal_breakdown() -> None:
    slip = compute_payslip(
        basic_salary=Decimal("50000.00"),
        house_rent_allowance=Decimal("25000.00"),
        medical_allowance=Decimal("5000.00"),
        conveyance_allowance=Decimal("3000.00"),
        pf_deduction_percent=Decimal("10.00"),
        tax_deduction_amount=Decimal("2500.00"),
    )
    assert slip.basic_salary == Decimal("50000.00")
    assert slip.allowances_total == Decimal("33000.00")
    assert slip.gross_salary == Decimal("83000.00")
    assert slip.pf_deduction == Decimal("5000.00")
    assert slip.tax_deduction == Decimal("2500.00")
    assert slip.total_deductions == Decimal("7500.00")
    assert slip.net_salary == Decimal("75500.00")


def test_compute_payslip_rejects_negative_net() -> None:
    with pytest.raises(BusinessRuleError, match="deductions cannot exceed gross"):
        compute_payslip(
            basic_salary=Decimal("10000.00"),
            tax_deduction_amount=Decimal("15000.00"),
        )
