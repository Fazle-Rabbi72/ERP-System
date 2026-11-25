"""Sales & Invoicing HTTP router (thin layer: no business logic)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_sales_service, require_permission
from app.core.permissions import (
    PERM_SALES_CUSTOMERS_READ,
    PERM_SALES_CUSTOMERS_WRITE,
    PERM_SALES_INVOICES_POST,
    PERM_SALES_INVOICES_READ,
    PERM_SALES_INVOICES_WRITE,
    PERM_SALES_PAYMENTS_WRITE,
)
from app.core.query import PaginationParams, SortParams, get_pagination_params, get_sort_params
from app.core.security import TokenPayload
from app.schemas.common import PaginatedResponse
from app.schemas.sales import (
    CustomerCreateRequest,
    CustomerPaymentCreateRequest,
    CustomerPaymentResponse,
    CustomerResponse,
    InvoiceStatus,
    SalesInvoiceCreateRequest,
    SalesInvoiceResponse,
)
from app.services.sales_service import SalesService

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("/customers", response_model=PaginatedResponse[CustomerResponse])
async def list_customers(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_SALES_CUSTOMERS_READ))],
    service: Annotated[SalesService, Depends(get_sales_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    search: Annotated[str | None, Query(max_length=128)] = None,
) -> PaginatedResponse[CustomerResponse]:
    items, total = await service.list_customers(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        search=search,
    )
    return PaginatedResponse[CustomerResponse].create(
        items=[CustomerResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_SALES_CUSTOMERS_WRITE))],
    service: Annotated[SalesService, Depends(get_sales_service)],
) -> CustomerResponse:
    customer = await service.create_customer(
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
    return CustomerResponse.model_validate(customer)


@router.get("/invoices", response_model=PaginatedResponse[SalesInvoiceResponse])
async def list_invoices(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_SALES_INVOICES_READ))],
    service: Annotated[SalesService, Depends(get_sales_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    status_filter: Annotated[InvoiceStatus | None, Query(alias="status")] = None,
    customer_id: Annotated[uuid.UUID | None, Query()] = None,
) -> PaginatedResponse[SalesInvoiceResponse]:
    items, total = await service.list_invoices(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        status_filter=status_filter,
        customer_id=customer_id,
    )
    return PaginatedResponse[SalesInvoiceResponse].create(
        items=[SalesInvoiceResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/invoices", response_model=SalesInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: SalesInvoiceCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_SALES_INVOICES_WRITE))],
    service: Annotated[SalesService, Depends(get_sales_service)],
) -> SalesInvoiceResponse:
    invoice = await service.create_invoice(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        customer_id=body.customer_id,
        invoice_date=body.invoice_date,
        due_date=body.due_date,
        notes=body.notes,
        lines=body.lines,
    )
    return SalesInvoiceResponse.model_validate(invoice)


@router.post("/invoices/{invoice_id}/post", response_model=SalesInvoiceResponse)
async def post_invoice(
    invoice_id: uuid.UUID,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_SALES_INVOICES_POST))],
    service: Annotated[SalesService, Depends(get_sales_service)],
) -> SalesInvoiceResponse:
    invoice = await service.post_invoice(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        invoice_id=invoice_id,
    )
    return SalesInvoiceResponse.model_validate(invoice)


@router.post(
    "/invoices/{invoice_id}/payments",
    response_model=CustomerPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_payment(
    invoice_id: uuid.UUID,
    body: CustomerPaymentCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_SALES_PAYMENTS_WRITE))],
    service: Annotated[SalesService, Depends(get_sales_service)],
) -> CustomerPaymentResponse:
    payment = await service.record_payment(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        invoice_id=invoice_id,
        payment_date=body.payment_date,
        amount=body.amount,
        payment_method=body.payment_method,
        deposit_account_id=body.deposit_account_id,
        reference=body.reference,
    )
    return CustomerPaymentResponse.model_validate(payment)
