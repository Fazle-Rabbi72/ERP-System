"""Unit tests for double-entry Decimal accounting rules and schema validation."""

import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.exceptions import BusinessRuleError
from app.schemas.accounting import JournalLineCreateRequest
from app.services.accounting_service import DEFAULT_BD_COA, validate_double_entry_balance

pytestmark = pytest.mark.unit


def test_journal_line_rejects_both_debit_and_credit_or_zero() -> None:
    acc = uuid.uuid4()
    with pytest.raises(ValidationError):
        JournalLineCreateRequest(account_id=acc, debit=Decimal("100.00"), credit=Decimal("100.00"))
    with pytest.raises(ValidationError):
        JournalLineCreateRequest(account_id=acc, debit=Decimal("0.00"), credit=Decimal("0.00"))


def test_double_entry_requires_exact_decimal_equality() -> None:
    a1, a2 = uuid.uuid4(), uuid.uuid4()
    balanced = [
        JournalLineCreateRequest(account_id=a1, debit=Decimal("125000.75")),
        JournalLineCreateRequest(account_id=a2, credit=Decimal("125000.75")),
    ]
    dr, cr = validate_double_entry_balance(balanced)
    assert dr == Decimal("125000.75")
    assert cr == Decimal("125000.75")

    unbalanced = [
        JournalLineCreateRequest(account_id=a1, debit=Decimal("100.01")),
        JournalLineCreateRequest(account_id=a2, credit=Decimal("100.00")),
    ]
    with pytest.raises(BusinessRuleError, match="not balanced"):
        validate_double_entry_balance(unbalanced)


def test_default_bd_coa_has_unique_codes_and_all_five_types() -> None:
    codes = [item.code for item in DEFAULT_BD_COA]
    assert len(codes) == len(set(codes))
    types = {item.account_type for item in DEFAULT_BD_COA}
    assert types == {"asset", "liability", "equity", "revenue", "expense"}
