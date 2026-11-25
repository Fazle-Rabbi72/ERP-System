"""Inventory & Warehouse service: SKU catalog, warehouses, stock ledger & valuation."""

import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.core.db import Database
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.query import (
    FilterRule,
    PaginationParams,
    SortParams,
    build_filters,
    build_order_by,
)
from app.models.inventory import Product, StockMovement, Warehouse
from app.repositories.inventory import (
    ProductRepository,
    StockLevelRow,
    StockMovementRepository,
    WarehouseRepository,
)
from app.schemas.inventory import MovementType
from app.services.audit_service import record_audit

ZERO_QTY = Decimal("0.000")
TWO_PLACES = Decimal("0.01")


def normalize_signed_quantity(movement_type: MovementType, quantity: Decimal) -> Decimal:
    """Convert raw input quantity to signed delta (+in, -out, non-zero adjustment)."""
    if quantity == ZERO_QTY:
        raise BusinessRuleError("Movement quantity cannot be zero.")
    if movement_type == "in":
        if quantity <= ZERO_QTY:
            raise BusinessRuleError("Stock IN quantity must be positive.")
        return quantity
    if movement_type == "out":
        if quantity <= ZERO_QTY:
            raise BusinessRuleError("Stock OUT quantity must be positive.")
        return -quantity
    return quantity


def compute_stock_value(on_hand: Decimal, unit_cost: Decimal) -> Decimal:
    return (on_hand * unit_cost).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class InventoryService:
    """All Inventory & Warehouse business rules live here."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def list_warehouses(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        search: str | None = None,
    ) -> tuple[list[Warehouse], int]:
        order_by = build_order_by(
            sort,
            allowed={"code": Warehouse.code, "name": Warehouse.name},
            default=[Warehouse.code.asc()],
        )
        filters = build_filters([FilterRule(column=Warehouse.name, operator="ilike", value=search)])
        async with self._database.transaction(tenant_id) as session:
            return await WarehouseRepository(session, tenant_id).list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def create_warehouse(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        code: str,
        name: str,
        location: str,
    ) -> Warehouse:
        cleaned_code = code.strip().upper()
        async with self._database.transaction(tenant_id) as session:
            repo = WarehouseRepository(session, tenant_id)
            if await repo.get_by_code(cleaned_code) is not None:
                raise ConflictError("A warehouse with this code already exists.")

            warehouse = await repo.create(
                Warehouse(
                    tenant_id=tenant_id,
                    code=cleaned_code,
                    name=name.strip(),
                    location=location.strip(),
                ),
                actor_id=actor_id,
            )
            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="inventory.warehouse.created",
                resource_type="warehouse",
                resource_id=warehouse.id,
                after_data={"code": warehouse.code, "name": warehouse.name},
            )
            return warehouse

    async def list_products(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        search: str | None = None,
    ) -> tuple[list[Product], int]:
        order_by = build_order_by(
            sort,
            allowed={"sku": Product.sku, "name": Product.name, "sale_price": Product.sale_price},
            default=[Product.sku.asc()],
        )
        filters = build_filters([FilterRule(column=Product.name, operator="ilike", value=search)])
        async with self._database.transaction(tenant_id) as session:
            return await ProductRepository(session, tenant_id).list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def create_product(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        sku: str,
        name: str,
        unit: str,
        unit_cost: Decimal,
        sale_price: Decimal,
        reorder_level: Decimal,
        description: str,
    ) -> Product:
        cleaned_sku = sku.strip().upper()
        async with self._database.transaction(tenant_id) as session:
            repo = ProductRepository(session, tenant_id)
            if await repo.get_by_sku(cleaned_sku) is not None:
                raise ConflictError("A product with this SKU already exists.")

            product = await repo.create(
                Product(
                    tenant_id=tenant_id,
                    sku=cleaned_sku,
                    name=name.strip(),
                    unit=unit.strip(),
                    unit_cost=unit_cost,
                    sale_price=sale_price,
                    reorder_level=reorder_level,
                    description=description.strip(),
                ),
                actor_id=actor_id,
            )
            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="inventory.product.created",
                resource_type="product",
                resource_id=product.id,
                after_data={
                    "sku": product.sku,
                    "name": product.name,
                    "unit_cost": unit_cost,
                    "sale_price": sale_price,
                },
            )
            return product

    async def list_movements(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        product_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        movement_type: MovementType | None = None,
    ) -> tuple[list[StockMovement], int]:
        order_by = build_order_by(
            sort,
            allowed={
                "movement_date": StockMovement.movement_date,
                "movement_no": StockMovement.movement_no,
                "created_at": StockMovement.created_at,
            },
            default=[StockMovement.movement_date.desc(), StockMovement.created_at.desc()],
        )
        filters = build_filters(
            [
                FilterRule(column=StockMovement.product_id, operator="eq", value=product_id),
                FilterRule(column=StockMovement.warehouse_id, operator="eq", value=warehouse_id),
                FilterRule(column=StockMovement.movement_type, operator="eq", value=movement_type),
            ]
        )
        async with self._database.transaction(tenant_id) as session:
            return await StockMovementRepository(session, tenant_id).list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def record_movement(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        movement_date: date,
        movement_type: MovementType,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        quantity: Decimal,
        unit_cost: Decimal,
        reference: str,
        notes: str,
    ) -> StockMovement:
        signed_qty = normalize_signed_quantity(movement_type, quantity)

        async with self._database.transaction(tenant_id) as session:
            product = await ProductRepository(session, tenant_id).get_by_id(product_id)
            if product is None or not product.is_active:
                raise NotFoundError("Product not found or inactive.")

            warehouse = await WarehouseRepository(session, tenant_id).get_by_id(warehouse_id)
            if warehouse is None or not warehouse.is_active:
                raise NotFoundError("Warehouse not found or inactive.")

            move_repo = StockMovementRepository(session, tenant_id)
            current_on_hand = await move_repo.get_on_hand(
                product_id=product_id,
                warehouse_id=warehouse_id,
            )
            if current_on_hand + signed_qty < ZERO_QTY:
                raise BusinessRuleError(
                    "Insufficient stock in warehouse for this movement.",
                    details={
                        "available": str(current_on_hand),
                        "requested_delta": str(signed_qty),
                    },
                )

            seq = await move_repo.next_movement_sequence(movement_date.year)
            movement_no = f"STK-{movement_date.year}-{seq:06d}"
            effective_cost = unit_cost if unit_cost > Decimal("0.00") else product.unit_cost

            movement = await move_repo.create(
                StockMovement(
                    tenant_id=tenant_id,
                    movement_no=movement_no,
                    movement_date=movement_date,
                    movement_type=movement_type,
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=signed_qty,
                    unit_cost=effective_cost,
                    reference=reference.strip(),
                    notes=notes.strip(),
                ),
                actor_id=actor_id,
            )
            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action=f"inventory.stock.{movement_type}",
                resource_type="stock_movement",
                resource_id=movement.id,
                before_data={"on_hand": current_on_hand},
                after_data={
                    "movement_no": movement.movement_no,
                    "product_sku": product.sku,
                    "warehouse_code": warehouse.code,
                    "delta": signed_qty,
                    "new_on_hand": current_on_hand + signed_qty,
                },
            )
            return movement

    async def get_stock_summary(
        self,
        *,
        tenant_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        low_stock_only: bool = False,
    ) -> list[StockLevelRow]:
        async with self._database.transaction(tenant_id) as session:
            rows = await StockMovementRepository(session, tenant_id).stock_summary(
                warehouse_id=warehouse_id
            )
        if low_stock_only:
            return [r for r in rows if r.on_hand <= r.reorder_level]
        return rows
