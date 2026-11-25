"""Accounting & General Ledger ORM models (Chart of Accounts + Double-Entry Journals)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MONEY_TYPE, TenantBaseModel


class Account(TenantBaseModel):
    """Chart of Accounts entry (hierarchical, tenant-scoped)."""

    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_accounts_tenant_code"),
        CheckConstraint(
            "account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')",
            name="valid_account_type",
        ),
        CheckConstraint(
            "normal_balance IN ('debit', 'credit')",
            name="valid_normal_balance",
        ),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    normal_balance: Mapped[str] = mapped_column(String(8), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    is_group: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
        server_default="",
    )


class JournalEntry(TenantBaseModel):
    """Double-entry journal voucher header.

    Posted entries are immutable; corrections MUST be recorded via a reversal entry.
    """

    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "voucher_no", name="uq_journal_entries_tenant_voucher_no"),
        CheckConstraint(
            "status IN ('draft', 'posted', 'reversed')",
            name="valid_journal_status",
        ),
    )

    voucher_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reference: Mapped[str] = mapped_column(
        String(128), nullable=False, default="", server_default=""
    )
    narration: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="draft",
        server_default="draft",
        index=True,
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    reversed_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="RESTRICT"),
        nullable=True,
    )

    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="entry",
        order_by="JournalLine.line_no",
        lazy="selectin",
    )


class JournalLine(TenantBaseModel):
    """Individual debit or credit line belonging to a JournalEntry."""

    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint("debit >= 0 AND credit >= 0", name="non_negative_amounts"),
        CheckConstraint(
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
            name="exclusive_debit_or_credit",
        ),
    )

    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
        server_default="",
    )
    debit: Mapped[Decimal] = mapped_column(
        MONEY_TYPE,
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
    )
    credit: Mapped[Decimal] = mapped_column(
        MONEY_TYPE,
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
    )

    entry: Mapped[JournalEntry] = relationship(back_populates="lines")
