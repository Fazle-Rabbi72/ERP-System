"""Inventory & Warehouse HTTP router (thin layer: no business logic)."""

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_inventory_service, require_permission
from app.core.permissions import (
    PERM_INVENTORY_PRODUCTS_READ,
    PERM_INVENTORY_PRODUCTS_WRITE,
    PERM_INVENTORY_STOCK_MOVE,
    PERM_INVENTORY_STOCK_READ,
    PERM_INVENTORY_WAREHOUSES_READ,
    PERM_INVENTORY_WAREHOUSES_WRITE,
)
from app.core.query import PaginationParams, SortParams, get_pagination_params, get_sort_params
from app.core.security import TokenPayload
from app.schemas.common import PaginatedResponse
from app.schemas.inventory import (
    MovementType,
    ProductCreateRequest,
    ProductResponse,
    StockMovementCreateRequest,
    StockMovementResponse,
    StockSummaryItemResponse,
    StockSummaryResponse,
    WarehouseCreateRequest,
    WarehouseResponse,
)
from app.services.inventory_service import InventoryService, compute_stock_value

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/warehouses", response_model=PaginatedResponse[WarehouseResponse])
async def list_warehouses(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_INVENTORY_WAREHOUSES_READ))],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    search: Annotated[str | None, Query(max_length=128)] = None,
) -> PaginatedResponse[WarehouseResponse]:
    items, total = await service.list_warehouses(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        search=search,
    )
    return PaginatedResponse[WarehouseResponse].create(
        items=[WarehouseResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    body: WarehouseCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_INVENTORY_WAREHOUSES_WRITE))],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> WarehouseResponse:
    wh = await service.create_warehouse(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        code=body.code,
        name=body.name,
        location=body.location,
    )
    return WarehouseResponse.model_validate(wh)


@router.get("/products", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_INVENTORY_PRODUCTS_READ))],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    search: Annotated[str | None, Query(max_length=128)] = None,
) -> PaginatedResponse[ProductResponse]:
    items, total = await service.list_products(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        search=search,
    )
    return PaginatedResponse[ProductResponse].create(
        items=[ProductResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_INVENTORY_PRODUCTS_WRITE))],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> ProductResponse:
    product = await service.create_product(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        sku=body.sku,
        name=body.name,
        unit=body.unit,
        unit_cost=body.unit_cost,
        sale_price=body.sale_price,
        reorder_level=body.reorder_level,
        description=body.description,
    )
    return ProductResponse.model_validate(product)


@router.get("/movements", response_model=PaginatedResponse[StockMovementResponse])
async def list_movements(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_INVENTORY_STOCK_READ))],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    product_id: Annotated[uuid.UUID | None, Query()] = None,
    warehouse_id: Annotated[uuid.UUID | None, Query()] = None,
    movement_type: Annotated[MovementType | None, Query()] = None,
) -> PaginatedResponse[StockMovementResponse]:
    items, total = await service.list_movements(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
    )
    return PaginatedResponse[StockMovementResponse].create(
        items=[StockMovementResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/movements", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED
)
async def record_movement(
    body: StockMovementCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_INVENTORY_STOCK_MOVE))],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> StockMovementResponse:
    movement = await service.record_movement(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        movement_date=body.movement_date,
        movement_type=body.movement_type,
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        quantity=body.quantity,
        unit_cost=body.unit_cost,
        reference=body.reference,
        notes=body.notes,
    )
    return StockMovementResponse.model_validate(movement)


@router.get("/stock-summary", response_model=StockSummaryResponse)
async def stock_summary(
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_INVENTORY_STOCK_READ))],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    warehouse_id: Annotated[uuid.UUID | None, Query()] = None,
    low_stock_only: Annotated[bool, Query()] = False,
) -> StockSummaryResponse:
    rows = await service.get_stock_summary(
        tenant_id=auth.tenant_id,
        warehouse_id=warehouse_id,
        low_stock_only=low_stock_only,
    )
    items: list[StockSummaryItemResponse] = []
    total_val = Decimal("0.00")
    low_count = 0
    for row in rows:
        val = compute_stock_value(row.on_hand, row.unit_cost)
        is_low = row.on_hand <= row.reorder_level
        total_val += val
        if is_low:
            low_count += 1
        items.append(
            StockSummaryItemResponse(
                product_id=row.product_id,
                sku=row.sku,
                product_name=row.product_name,
                unit=row.unit,
                warehouse_id=row.warehouse_id,
                warehouse_code=row.warehouse_code,
                warehouse_name=row.warehouse_name,
                on_hand=row.on_hand,
                reorder_level=row.reorder_level,
                unit_cost=row.unit_cost,
                stock_value=val,
                is_low_stock=is_low,
            )
        )
    return StockSummaryResponse(
        items=items,
        total_valuation=total_val,
        low_stock_count=low_count,
    )
