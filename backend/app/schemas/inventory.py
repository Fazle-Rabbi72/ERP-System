"""Pydantic schemas for Inventory & Warehouse."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

MovementType = Literal["in", "out", "adjustment"]
_TWO_PLACES = Decimal("0.01")


def _fmt_money(value: Decimal) -> str:
    return str(value.quantize(_TWO_PLACES))


class WarehouseCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    location: str = Field(default="", max_length=500)


class WarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    location: str
    is_active: bool
    created_at: datetime


class ProductCreateRequest(BaseModel):
    sku: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=255)
    unit: str = Field(default="pcs", min_length=1, max_length=32)
    unit_cost: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2)
    sale_price: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2)
    reorder_level: Decimal = Field(default=Decimal("0.000"), ge=Decimal("0.000"), decimal_places=3)
    description: str = Field(default="", max_length=500)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str
    unit: str
    unit_cost: Decimal
    sale_price: Decimal
    reorder_level: Decimal
    is_active: bool
    description: str
    created_at: datetime

    @field_serializer("unit_cost", "sale_price")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)

    @field_serializer("reorder_level")
    def _serialize_qty(self, value: Decimal) -> str:
        return str(value)


class StockMovementCreateRequest(BaseModel):
    movement_date: date
    movement_type: MovementType
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal = Field(decimal_places=3)
    unit_cost: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2)
    reference: str = Field(default="", max_length=128)
    notes: str = Field(default="", max_length=500)


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    movement_no: str
    movement_date: date
    movement_type: MovementType
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal
    unit_cost: Decimal
    reference: str
    notes: str
    created_at: datetime

    @field_serializer("unit_cost")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)

    @field_serializer("quantity")
    def _serialize_qty(self, value: Decimal) -> str:
        return str(value)


class StockSummaryItemResponse(BaseModel):
    product_id: uuid.UUID
    sku: str
    product_name: str
    unit: str
    warehouse_id: uuid.UUID
    warehouse_code: str
    warehouse_name: str
    on_hand: Decimal
    reorder_level: Decimal
    unit_cost: Decimal
    stock_value: Decimal
    is_low_stock: bool

    @field_serializer("unit_cost", "stock_value")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)

    @field_serializer("on_hand", "reorder_level")
    def _serialize_qty(self, value: Decimal) -> str:
        return str(value)


class StockSummaryResponse(BaseModel):
    items: list[StockSummaryItemResponse]
    total_valuation: Decimal
    low_stock_count: int

    @field_serializer("total_valuation")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)
