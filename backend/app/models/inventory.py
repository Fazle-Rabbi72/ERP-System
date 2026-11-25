"""Inventory & Warehouse ORM models (Warehouse, Product, StockMovement)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MONEY_TYPE, TenantBaseModel


class Warehouse(TenantBaseModel):
    __tablename__ = "warehouses"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_warehouses_tenant_code"),)

    code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", server_default=""
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )


class Product(TenantBaseModel):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_products_tenant_sku"),
        CheckConstraint(
            "unit_cost >= 0 AND sale_price >= 0 AND reorder_level >= 0",
            name="non_negative_product_values",
        ),
    )

    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pcs", server_default="pcs"
    )
    unit_cost: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    sale_price: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(18, 3, asdecimal=True),
        nullable=False,
        default=Decimal("0.000"),
        server_default=text("0.000"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    description: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", server_default=""
    )


class StockMovement(TenantBaseModel):
    """Signed stock ledger entry (+ for stock in, - for stock out)."""

    __tablename__ = "stock_movements"
    __table_args__ = (
        UniqueConstraint("tenant_id", "movement_no", name="uq_stock_movements_tenant_movement_no"),
        CheckConstraint(
            "movement_type IN ('in', 'out', 'adjustment')",
            name="valid_movement_type",
        ),
        CheckConstraint("quantity <> 0", name="non_zero_movement_quantity"),
        CheckConstraint("unit_cost >= 0", name="non_negative_movement_cost"),
    )

    movement_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    movement_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3, asdecimal=True), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    reference: Mapped[str] = mapped_column(
        String(128), nullable=False, default="", server_default=""
    )
    notes: Mapped[str] = mapped_column(String(500), nullable=False, default="", server_default="")
