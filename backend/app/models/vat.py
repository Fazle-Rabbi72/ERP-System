"""Configurable VAT rate profiles (never hardcoding statutory NBR tax rates)."""

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBaseModel


class VatRate(TenantBaseModel):
    __tablename__ = "vat_rates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_vat_rates_tenant_code"),
        CheckConstraint("rate_percent >= 0 AND rate_percent <= 100", name="valid_vat_rate_pct"),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2, asdecimal=True), nullable=False)
    is_vds_applicable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    statutory_note: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", server_default=""
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
