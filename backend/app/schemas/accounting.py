"""Pydantic schemas for Accounting & General Ledger.

All monetary fields use `Decimal` and serialize as exact strings so precision
is never lost in JSON or JavaScript.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

AccountType = Literal["asset", "liability", "equity", "revenue", "expense"]
NormalBalance = Literal["debit", "credit"]
JournalStatus = Literal["draft", "posted", "reversed"]

_TWO_PLACES = Decimal("0.01")


def _fmt_money(value: Decimal) -> str:
    return str(value.quantize(_TWO_PLACES))


class AccountCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    account_type: AccountType
    parent_id: uuid.UUID | None = None
    is_group: bool = False
    description: str = Field(default="", max_length=500)


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    account_type: AccountType
    normal_balance: NormalBalance
    parent_id: uuid.UUID | None
    is_group: bool
    is_active: bool
    description: str
    created_at: datetime


class SeedCoaResponse(BaseModel):
    created_count: int
    total_accounts: int


class JournalLineCreateRequest(BaseModel):
    account_id: uuid.UUID
    description: str = Field(default="", max_length=500)
    debit: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2)
    credit: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2)

    @model_validator(mode="after")
    def _validate_exclusive_side(self) -> "JournalLineCreateRequest":
        has_debit = self.debit > Decimal("0.00")
        has_credit = self.credit > Decimal("0.00")
        if has_debit == has_credit:
            msg = "Each journal line must have either a positive debit or a positive credit."
            raise ValueError(msg)
        return self


class JournalEntryCreateRequest(BaseModel):
    entry_date: date
    reference: str = Field(default="", max_length=128)
    narration: str = Field(min_length=2, max_length=1000)
    lines: list[JournalLineCreateRequest] = Field(min_length=2)


class JournalLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    line_no: int
    description: str
    debit: Decimal
    credit: Decimal

    @field_serializer("debit", "credit")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class JournalEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    voucher_no: str
    entry_date: date
    reference: str
    narration: str
    status: JournalStatus
    posted_at: datetime | None
    posted_by: uuid.UUID | None
    reversed_entry_id: uuid.UUID | None
    lines: list[JournalLineResponse]
    created_at: datetime


class TrialBalanceLineResponse(BaseModel):
    account_id: uuid.UUID
    code: str
    name: str
    account_type: AccountType
    normal_balance: NormalBalance
    total_debit: Decimal
    total_credit: Decimal
    net_debit: Decimal
    net_credit: Decimal

    @field_serializer("total_debit", "total_credit", "net_debit", "net_credit")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class TrialBalanceResponse(BaseModel):
    as_of_date: date | None
    rows: list[TrialBalanceLineResponse]
    grand_total_debit: Decimal
    grand_total_credit: Decimal
    is_balanced: bool

    @field_serializer("grand_total_debit", "grand_total_credit")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)
