"""Purchase & Supplier HTTP router (thin layer: no business logic)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_purchase_service, require_permission
from app.core.permissions import (
    PERM_PURCHASE_BILLS_POST,
    PERM_PURCHASE_BILLS_READ,
    PERM_PURCHASE_BILLS_WRITE,
    PERM_PURCHASE_PAYMENTS_WRITE,
    PERM_PURCHASE_SUPPLIERS_READ,
    PERM_PURCHASE_SUPPLIERS_WRITE,
)
from app.core.query import PaginationParams, SortParams, get_pagination_params, get_sort_params
from app.core.security import TokenPayload
from app.schemas.common import PaginatedResponse
from app.schemas.purchase import (
    BillStatus,
    PurchaseBillCreateRequest,
    PurchaseBillResponse,
    SupplierCreateRequest,
    SupplierPaymentCreateRequest,
    SupplierPaymentResponse,
    SupplierResponse,
)
from app.services.purchase_service import PurchaseService

router = APIRouter(prefix="/purchase", tags=["purchase"])


@router.get("/suppliers", response_model=PaginatedResponse[SupplierResponse])
async def list_suppliers(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_PURCHASE_SUPPLIERS_READ))],
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    search: Annotated[str | None, Query(max_length=128)] = None,
) -> PaginatedResponse[SupplierResponse]:
    items, total = await service.list_suppliers(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        search=search,
    )
    return PaginatedResponse[SupplierResponse].create(
        items=[SupplierResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    body: SupplierCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_PURCHASE_SUPPLIERS_WRITE))],
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
) -> SupplierResponse:
    supplier = await service.create_supplier(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        code=body.code,
        name=body.name,
        phone=body.phone,
        email=body.email,
        address=body.address,
        bin_no=body.bin_no,
        tin_no=body.tin_no,
    )
    return SupplierResponse.model_validate(supplier)


@router.get("/bills", response_model=PaginatedResponse[PurchaseBillResponse])
async def list_bills(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_PURCHASE_BILLS_READ))],
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    status_filter: Annotated[BillStatus | None, Query(alias="status")] = None,
    supplier_id: Annotated[uuid.UUID | None, Query()] = None,
) -> PaginatedResponse[PurchaseBillResponse]:
    items, total = await service.list_bills(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        status_filter=status_filter,
        supplier_id=supplier_id,
    )
    return PaginatedResponse[PurchaseBillResponse].create(
        items=[PurchaseBillResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/bills", response_model=PurchaseBillResponse, status_code=status.HTTP_201_CREATED)
async def create_bill(
    body: PurchaseBillCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_PURCHASE_BILLS_WRITE))],
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
) -> PurchaseBillResponse:
    bill = await service.create_bill(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        supplier_id=body.supplier_id,
        expense_account_id=body.expense_account_id,
        supplier_bill_ref=body.supplier_bill_ref,
        bill_date=body.bill_date,
        due_date=body.due_date,
        tds_rate_percent=body.tds_rate_percent,
        vds_rate_percent=body.vds_rate_percent,
        notes=body.notes,
        lines=body.lines,
    )
    return PurchaseBillResponse.model_validate(bill)


@router.post("/bills/{bill_id}/post", response_model=PurchaseBillResponse)
async def post_bill(
    bill_id: uuid.UUID,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_PURCHASE_BILLS_POST))],
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
) -> PurchaseBillResponse:
    bill = await service.post_bill(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        bill_id=bill_id,
    )
    return PurchaseBillResponse.model_validate(bill)


@router.post(
    "/bills/{bill_id}/payments",
    response_model=SupplierPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_payment(
    bill_id: uuid.UUID,
    body: SupplierPaymentCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_PURCHASE_PAYMENTS_WRITE))],
    service: Annotated[PurchaseService, Depends(get_purchase_service)],
) -> SupplierPaymentResponse:
    payment = await service.record_payment(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        bill_id=bill_id,
        payment_date=body.payment_date,
        amount=body.amount,
        payment_method=body.payment_method,
        payment_account_id=body.payment_account_id,
        reference=body.reference,
    )
    return SupplierPaymentResponse.model_validate(payment)
