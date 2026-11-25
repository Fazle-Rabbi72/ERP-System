"""Sales & Invoicing ORM models (Customer, SalesInvoice, SalesInvoiceLine, CustomerPayment)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MONEY_TYPE, TenantBaseModel


class Customer(TenantBaseModel):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_customers_tenant_code"),)

    code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    address: Mapped[str] = mapped_column(String(500), nullable=False, default="", server_default="")
    bin_no: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
    tin_no: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )


class SalesInvoice(TenantBaseModel):
    __tablename__ = "sales_invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_no", name="uq_sales_invoices_tenant_invoice_no"),
        CheckConstraint(
            "status IN ('draft', 'posted', 'partially_paid', 'paid', 'cancelled')",
            name="valid_invoice_status",
        ),
        CheckConstraint(
            "subtotal >= 0 AND vat_total >= 0 AND grand_total >= 0 AND paid_amount >= 0",
            name="non_negative_totals",
        ),
        CheckConstraint("paid_amount <= grand_total", name="paid_not_exceeding_total"),
    )

    invoice_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
        index=True,
    )
    subtotal: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    vat_total: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    grand_total: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    notes: Mapped[str] = mapped_column(String(1000), nullable=False, default="", server_default="")
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="RESTRICT"),
        nullable=True,
    )

    lines: Mapped[list["SalesInvoiceLine"]] = relationship(
        back_populates="invoice",
        order_by="SalesInvoiceLine.line_no",
        lazy="selectin",
    )


class SalesInvoiceLine(TenantBaseModel):
    __tablename__ = "sales_invoice_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0 AND unit_price >= 0", name="positive_qty_non_neg_price"),
        CheckConstraint(
            "vat_rate_percent >= 0 AND vat_rate_percent <= 100",
            name="valid_vat_rate_range",
        ),
    )

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sales_invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3, asdecimal=True), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    vat_rate_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2, asdecimal=True),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
    )
    line_subtotal: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    line_vat: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)

    invoice: Mapped[SalesInvoice] = relationship(back_populates="lines")


class CustomerPayment(TenantBaseModel):
    __tablename__ = "customer_payments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "payment_no", name="uq_customer_payments_tenant_payment_no"),
        CheckConstraint("amount > 0", name="positive_payment_amount"),
        CheckConstraint(
            "payment_method IN ('cash', 'bank', 'mfs', 'cheque')",
            name="valid_payment_method",
        ),
    )

    payment_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sales_invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(16), nullable=False)
    deposit_account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reference: Mapped[str] = mapped_column(
        String(128), nullable=False, default="", server_default=""
    )
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="RESTRICT"),
        nullable=True,
    )
