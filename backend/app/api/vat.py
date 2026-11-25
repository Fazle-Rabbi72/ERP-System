"""Bangladesh VAT & Mushak HTTP router (thin layer: no business logic)."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_vat_service, require_permission
from app.core.permissions import (
    PERM_VAT_RATES_READ,
    PERM_VAT_RATES_WRITE,
    PERM_VAT_REPORTS_READ,
)
from app.core.query import PaginationParams, SortParams, get_pagination_params, get_sort_params
from app.core.security import TokenPayload
from app.schemas.common import PaginatedResponse
from app.schemas.vat import (
    Mushak61ItemResponse,
    Mushak61ReportResponse,
    Mushak62ItemResponse,
    Mushak62ReportResponse,
    Mushak63ChallanResponse,
    Mushak63LineResponse,
    Mushak91SummaryResponse,
    VatRateCreateRequest,
    VatRateResponse,
)
from app.services.vat_service import (
    MUSHAK_91_ADVISORY,
    ZERO,
    VatService,
    compute_net_vat_position,
)

router = APIRouter(prefix="/vat", tags=["vat"])


@router.get("/rates", response_model=PaginatedResponse[VatRateResponse])
async def list_vat_rates(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_VAT_RATES_READ))],
    service: Annotated[VatService, Depends(get_vat_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    search: Annotated[str | None, Query(max_length=128)] = None,
) -> PaginatedResponse[VatRateResponse]:
    items, total = await service.list_rates(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        search=search,
    )
    return PaginatedResponse[VatRateResponse].create(
        items=[VatRateResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/rates", response_model=VatRateResponse, status_code=status.HTTP_201_CREATED)
async def create_vat_rate(
    body: VatRateCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_VAT_RATES_WRITE))],
    service: Annotated[VatService, Depends(get_vat_service)],
) -> VatRateResponse:
    rate = await service.create_rate(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        code=body.code,
        name=body.name,
        rate_percent=body.rate_percent,
        is_vds_applicable=body.is_vds_applicable,
        statutory_note=body.statutory_note,
    )
    return VatRateResponse.model_validate(rate)


@router.get("/mushak/6-1", response_model=Mushak61ReportResponse)
async def mushak_61_purchase_register(
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_VAT_REPORTS_READ))],
    service: Annotated[VatService, Depends(get_vat_service)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Mushak61ReportResponse:
    rows = await service.get_mushak_61(
        tenant_id=auth.tenant_id,
        date_from=date_from,
        date_to=date_to,
    )
    return Mushak61ReportResponse(
        date_from=date_from,
        date_to=date_to,
        items=[
            Mushak61ItemResponse(
                bill_id=r.bill_id,
                bill_no=r.bill_no,
                bill_date=r.bill_date,
                supplier_bill_ref=r.supplier_bill_ref,
                supplier_name=r.supplier_name,
                supplier_bin=r.supplier_bin,
                taxable_value=r.taxable_value,
                input_vat=r.input_vat,
                vds_amount=r.vds_amount,
                tds_amount=r.tds_amount,
                gross_total=r.gross_total,
            )
            for r in rows
        ],
        total_taxable_value=sum((r.taxable_value for r in rows), ZERO),
        total_input_vat=sum((r.input_vat for r in rows), ZERO),
        total_vds=sum((r.vds_amount for r in rows), ZERO),
        total_tds=sum((r.tds_amount for r in rows), ZERO),
    )


@router.get("/mushak/6-2", response_model=Mushak62ReportResponse)
async def mushak_62_sales_register(
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_VAT_REPORTS_READ))],
    service: Annotated[VatService, Depends(get_vat_service)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Mushak62ReportResponse:
    rows = await service.get_mushak_62(
        tenant_id=auth.tenant_id,
        date_from=date_from,
        date_to=date_to,
    )
    return Mushak62ReportResponse(
        date_from=date_from,
        date_to=date_to,
        items=[
            Mushak62ItemResponse(
                invoice_id=r.invoice_id,
                invoice_no=r.invoice_no,
                invoice_date=r.invoice_date,
                customer_name=r.customer_name,
                customer_bin=r.customer_bin,
                taxable_value=r.taxable_value,
                output_vat=r.output_vat,
                grand_total=r.grand_total,
            )
            for r in rows
        ],
        total_taxable_value=sum((r.taxable_value for r in rows), ZERO),
        total_output_vat=sum((r.output_vat for r in rows), ZERO),
        total_grand_total=sum((r.grand_total for r in rows), ZERO),
    )


@router.get("/mushak/6-3/{invoice_id}", response_model=Mushak63ChallanResponse)
async def mushak_63_tax_invoice(
    invoice_id: uuid.UUID,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_VAT_REPORTS_READ))],
    service: Annotated[VatService, Depends(get_vat_service)],
) -> Mushak63ChallanResponse:
    data = await service.get_mushak_63(tenant_id=auth.tenant_id, invoice_id=invoice_id)
    return Mushak63ChallanResponse(
        invoice_id=data.invoice_id,
        invoice_no=data.invoice_no,
        invoice_date=data.invoice_date,
        seller_name=data.seller_name,
        customer_name=data.customer_name,
        customer_bin=data.customer_bin,
        customer_address=data.customer_address,
        lines=[
            Mushak63LineResponse(
                line_no=ln[0],
                description=ln[1],
                quantity=ln[2],
                unit_price=ln[3],
                vat_rate_percent=ln[4],
                line_subtotal=ln[5],
                line_vat=ln[6],
                line_total=ln[7],
            )
            for ln in data.lines
        ],
        subtotal=data.subtotal,
        vat_total=data.vat_total,
        grand_total=data.grand_total,
    )


@router.get("/mushak/9-1", response_model=Mushak91SummaryResponse)
async def mushak_91_summary(
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_VAT_REPORTS_READ))],
    service: Annotated[VatService, Depends(get_vat_service)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Mushak91SummaryResponse:
    purchases = await service.get_mushak_61(
        tenant_id=auth.tenant_id,
        date_from=date_from,
        date_to=date_to,
    )
    sales = await service.get_mushak_62(
        tenant_id=auth.tenant_id,
        date_from=date_from,
        date_to=date_to,
    )
    output_vat = sum((r.output_vat for r in sales), ZERO)
    input_vat = sum((r.input_vat for r in purchases), ZERO)
    payable, credit = compute_net_vat_position(output_vat, input_vat)
    return Mushak91SummaryResponse(
        date_from=date_from,
        date_to=date_to,
        total_sales_taxable=sum((r.taxable_value for r in sales), ZERO),
        total_output_vat=output_vat,
        total_purchase_taxable=sum((r.taxable_value for r in purchases), ZERO),
        total_input_vat=input_vat,
        net_vat_payable=payable,
        carry_forward_credit=credit,
        total_vds_payable=sum((r.vds_amount for r in purchases), ZERO),
        total_tds_payable=sum((r.tds_amount for r in purchases), ZERO),
        advisory_note=MUSHAK_91_ADVISORY,
    )
