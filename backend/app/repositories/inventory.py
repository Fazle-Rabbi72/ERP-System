"""Repositories for Inventory & Warehouse (warehouses, products, stock movements & levels)."""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import Product, StockMovement, Warehouse
from app.repositories.base import BaseRepository


@dataclass(frozen=True, slots=True)
class StockLevelRow:
    product_id: uuid.UUID
    sku: str
    product_name: str
    unit: str
    unit_cost: Decimal
    reorder_level: Decimal
    warehouse_id: uuid.UUID
    warehouse_code: str
    warehouse_name: str
    on_hand: Decimal


class WarehouseRepository(BaseRepository[Warehouse]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, Warehouse)

    async def get_by_code(self, code: str) -> Warehouse | None:
        stmt = self._base_query().where(Warehouse.code == code)
        return (await self._session.execute(stmt)).scalar_one_or_none()


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, Product)

    async def get_by_sku(self, sku: str) -> Product | None:
        stmt = self._base_query().where(Product.sku == sku)
        return (await self._session.execute(stmt)).scalar_one_or_none()


class StockMovementRepository(BaseRepository[StockMovement]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, StockMovement)

    async def next_movement_sequence(self, year: int) -> int:
        prefix = f"STK-{year}-"
        stmt = select(func.count(StockMovement.id)).where(
            StockMovement.tenant_id == self._tenant_id,
            StockMovement.movement_no.like(f"{prefix}%"),
        )
        return int((await self._session.execute(stmt)).scalar_one()) + 1

    async def get_on_hand(self, *, product_id: uuid.UUID, warehouse_id: uuid.UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(StockMovement.quantity), Decimal("0.000"))).where(
            StockMovement.tenant_id == self._tenant_id,
            StockMovement.is_deleted.is_(False),
            StockMovement.product_id == product_id,
            StockMovement.warehouse_id == warehouse_id,
        )
        return Decimal((await self._session.execute(stmt)).scalar_one())

    async def stock_summary(
        self,
        *,
        warehouse_id: uuid.UUID | None = None,
    ) -> list[StockLevelRow]:
        stmt = (
            select(
                Product.id.label("product_id"),
                Product.sku,
                Product.name.label("product_name"),
                Product.unit,
                Product.unit_cost,
                Product.reorder_level,
                Warehouse.id.label("warehouse_id"),
                Warehouse.code.label("warehouse_code"),
                Warehouse.name.label("warehouse_name"),
                func.coalesce(func.sum(StockMovement.quantity), Decimal("0.000")).label("on_hand"),
            )
            .join(StockMovement, StockMovement.product_id == Product.id)
            .join(Warehouse, Warehouse.id == StockMovement.warehouse_id)
            .where(
                Product.tenant_id == self._tenant_id,
                Product.is_deleted.is_(False),
                Warehouse.tenant_id == self._tenant_id,
                Warehouse.is_deleted.is_(False),
                StockMovement.tenant_id == self._tenant_id,
                StockMovement.is_deleted.is_(False),
            )
            .group_by(
                Product.id,
                Product.sku,
                Product.name,
                Product.unit,
                Product.unit_cost,
                Product.reorder_level,
                Warehouse.id,
                Warehouse.code,
                Warehouse.name,
            )
            .order_by(Product.sku.asc(), Warehouse.code.asc())
        )
        if warehouse_id is not None:
            stmt = stmt.where(Warehouse.id == warehouse_id)

        rows = (await self._session.execute(stmt)).all()
        return [
            StockLevelRow(
                product_id=row.product_id,
                sku=row.sku,
                product_name=row.product_name,
                unit=row.unit,
                unit_cost=Decimal(row.unit_cost),
                reorder_level=Decimal(row.reorder_level),
                warehouse_id=row.warehouse_id,
                warehouse_code=row.warehouse_code,
                warehouse_name=row.warehouse_name,
                on_hand=Decimal(row.on_hand),
            )
            for row in rows
        ]
