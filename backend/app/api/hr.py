"""HR & Payroll API routes (thin layer: no business logic)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_hr_service, require_permission
from app.core.permissions import (
    PERM_HR_EMPLOYEES_READ,
    PERM_HR_EMPLOYEES_WRITE,
    PERM_HR_PAYROLL_POST,
    PERM_HR_PAYROLL_READ,
    PERM_HR_PAYROLL_WRITE,
)
from app.core.query import PaginationParams, SortParams, get_pagination_params, get_sort_params
from app.core.security import TokenPayload
from app.models.hr import Employee, PayrollLine, PayrollRun
from app.schemas.common import PaginatedResponse
from app.schemas.hr import (
    EmployeeCreateRequest,
    EmployeeResponse,
    PayrollLineResponse,
    PayrollRunCreateRequest,
    PayrollRunDetailResponse,
    PayrollRunPostRequest,
    PayrollRunResponse,
)
from app.services.hr_service import PAYROLL_ADVISORY_NOTE, HrService

router = APIRouter(prefix="/hr", tags=["hr"])


def _to_detail_response(
    run: PayrollRun, pairs: list[tuple[PayrollLine, Employee]]
) -> PayrollRunDetailResponse:
    base = PayrollRunResponse.model_validate(run)
    return PayrollRunDetailResponse(
        **base.model_dump(),
        lines=[
            PayrollLineResponse(
                id=line.id,
                employee_id=emp.id,
                employee_code=emp.employee_code,
                employee_name=emp.full_name,
                designation=emp.designation,
                basic_salary=line.basic_salary,
                allowances_total=line.allowances_total,
                gross_salary=line.gross_salary,
                pf_deduction=line.pf_deduction,
                tax_deduction=line.tax_deduction,
                other_deduction=line.other_deduction,
                total_deductions=line.total_deductions,
                net_salary=line.net_salary,
            )
            for line, emp in pairs
        ],
        advisory_note=PAYROLL_ADVISORY_NOTE,
    )


@router.get("/employees", response_model=PaginatedResponse[EmployeeResponse])
async def list_employees(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_HR_EMPLOYEES_READ))],
    service: Annotated[HrService, Depends(get_hr_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    search: Annotated[str | None, Query(max_length=128)] = None,
) -> PaginatedResponse[EmployeeResponse]:
    items, total = await service.list_employees(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        search=search,
    )
    return PaginatedResponse[EmployeeResponse].create(
        items=[EmployeeResponse.model_validate(emp) for emp in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    body: EmployeeCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_HR_EMPLOYEES_WRITE))],
    service: Annotated[HrService, Depends(get_hr_service)],
) -> EmployeeResponse:
    emp = await service.create_employee(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        employee_code=body.employee_code,
        full_name=body.full_name,
        designation=body.designation,
        department=body.department,
        email=body.email,
        phone=body.phone,
        nid_no=body.nid_no,
        tin_no=body.tin_no,
        join_date=body.join_date,
        basic_salary=body.basic_salary,
        house_rent_allowance=body.house_rent_allowance,
        medical_allowance=body.medical_allowance,
        conveyance_allowance=body.conveyance_allowance,
        other_allowance=body.other_allowance,
        pf_deduction_percent=body.pf_deduction_percent,
        tax_deduction_amount=body.tax_deduction_amount,
    )
    return EmployeeResponse.model_validate(emp)


@router.get("/payroll-runs", response_model=PaginatedResponse[PayrollRunResponse])
async def list_payroll_runs(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_HR_PAYROLL_READ))],
    service: Annotated[HrService, Depends(get_hr_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
) -> PaginatedResponse[PayrollRunResponse]:
    items, total = await service.list_payroll_runs(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
    )
    return PaginatedResponse[PayrollRunResponse].create(
        items=[PayrollRunResponse.model_validate(run) for run in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/payroll-runs", response_model=PayrollRunDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_payroll_run(
    body: PayrollRunCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_HR_PAYROLL_WRITE))],
    service: Annotated[HrService, Depends(get_hr_service)],
) -> PayrollRunDetailResponse:
    run, pairs = await service.create_payroll_run(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        pay_year=body.pay_year,
        pay_month=body.pay_month,
        notes=body.notes,
    )
    return _to_detail_response(run, pairs)


@router.get("/payroll-runs/{run_id}", response_model=PayrollRunDetailResponse)
async def get_payroll_run_detail(
    run_id: uuid.UUID,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_HR_PAYROLL_READ))],
    service: Annotated[HrService, Depends(get_hr_service)],
) -> PayrollRunDetailResponse:
    run, pairs = await service.get_payroll_run_detail(
        tenant_id=auth.tenant_id,
        run_id=run_id,
    )
    return _to_detail_response(run, pairs)


@router.post("/payroll-runs/{run_id}/post", response_model=PayrollRunResponse)
async def post_payroll_run(
    run_id: uuid.UUID,
    body: PayrollRunPostRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_HR_PAYROLL_POST))],
    service: Annotated[HrService, Depends(get_hr_service)],
) -> PayrollRunResponse:
    run = await service.post_payroll_run(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        run_id=run_id,
        salary_expense_account_id=body.salary_expense_account_id,
        payment_account_id=body.payment_account_id,
        deductions_payable_account_id=body.deductions_payable_account_id,
    )
    return PayrollRunResponse.model_validate(run)
