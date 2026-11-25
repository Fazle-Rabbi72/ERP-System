"""Accounting & General Ledger HTTP router (thin layer: no business logic)."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_accounting_service, require_permission
from app.core.permissions import (
    PERM_ACCOUNTING_ACCOUNTS_READ,
    PERM_ACCOUNTING_ACCOUNTS_WRITE,
    PERM_ACCOUNTING_JOURNALS_POST,
    PERM_ACCOUNTING_JOURNALS_READ,
    PERM_ACCOUNTING_JOURNALS_WRITE,
    PERM_ACCOUNTING_REPORTS_READ,
)
from app.core.query import PaginationParams, SortParams, get_pagination_params, get_sort_params
from app.core.security import TokenPayload
from app.schemas.accounting import (
    AccountCreateRequest,
    AccountResponse,
    AccountType,
    JournalEntryCreateRequest,
    JournalEntryResponse,
    JournalStatus,
    SeedCoaResponse,
    TrialBalanceLineResponse,
    TrialBalanceResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.accounting_service import ZERO, AccountingService

router = APIRouter(prefix="/accounting", tags=["accounting"])


@router.post("/accounts/seed-default", response_model=SeedCoaResponse)
async def seed_default_accounts(
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_ACCOUNTING_ACCOUNTS_WRITE))],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> SeedCoaResponse:
    created, total = await service.seed_default_coa(tenant_id=auth.tenant_id, actor_id=auth.sub)
    return SeedCoaResponse(created_count=created, total_accounts=total)


@router.get("/accounts", response_model=PaginatedResponse[AccountResponse])
async def list_accounts(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_ACCOUNTING_ACCOUNTS_READ))],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    account_type: Annotated[AccountType | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=128)] = None,
) -> PaginatedResponse[AccountResponse]:
    items, total = await service.list_accounts(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        account_type=account_type,
        search=search,
    )
    return PaginatedResponse[AccountResponse].create(
        items=[AccountResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: AccountCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_ACCOUNTING_ACCOUNTS_WRITE))],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> AccountResponse:
    account = await service.create_account(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        code=body.code,
        name=body.name,
        account_type=body.account_type,
        parent_id=body.parent_id,
        is_group=body.is_group,
        description=body.description,
    )
    return AccountResponse.model_validate(account)


@router.get("/journals", response_model=PaginatedResponse[JournalEntryResponse])
async def list_journals(
    *,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_ACCOUNTING_JOURNALS_READ))],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    sort: Annotated[SortParams, Depends(get_sort_params)],
    status_filter: Annotated[JournalStatus | None, Query(alias="status")] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> PaginatedResponse[JournalEntryResponse]:
    items, total = await service.list_journal_entries(
        tenant_id=auth.tenant_id,
        pagination=pagination,
        sort=sort,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
    )
    return PaginatedResponse[JournalEntryResponse].create(
        items=[JournalEntryResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/journals", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_journal(
    body: JournalEntryCreateRequest,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_ACCOUNTING_JOURNALS_WRITE))],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> JournalEntryResponse:
    entry = await service.create_journal_entry(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        entry_date=body.entry_date,
        reference=body.reference,
        narration=body.narration,
        lines=body.lines,
    )
    return JournalEntryResponse.model_validate(entry)


@router.post("/journals/{entry_id}/post", response_model=JournalEntryResponse)
async def post_journal(
    entry_id: uuid.UUID,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_ACCOUNTING_JOURNALS_POST))],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> JournalEntryResponse:
    entry = await service.post_journal_entry(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        entry_id=entry_id,
    )
    return JournalEntryResponse.model_validate(entry)


@router.post("/journals/{entry_id}/reverse", response_model=JournalEntryResponse)
async def reverse_journal(
    entry_id: uuid.UUID,
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_ACCOUNTING_JOURNALS_POST))],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
) -> JournalEntryResponse:
    reversal = await service.reverse_journal_entry(
        tenant_id=auth.tenant_id,
        actor_id=auth.sub,
        entry_id=entry_id,
    )
    return JournalEntryResponse.model_validate(reversal)


@router.get("/reports/trial-balance", response_model=TrialBalanceResponse)
async def trial_balance(
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_ACCOUNTING_REPORTS_READ))],
    service: Annotated[AccountingService, Depends(get_accounting_service)],
    as_of_date: Annotated[date | None, Query()] = None,
) -> TrialBalanceResponse:
    report = await service.get_trial_balance(tenant_id=auth.tenant_id, as_of_date=as_of_date)
    rows: list[TrialBalanceLineResponse] = []
    for row in report.rows:
        diff = row.total_debit - row.total_credit
        rows.append(
            TrialBalanceLineResponse(
                account_id=row.account_id,
                code=row.code,
                name=row.name,
                account_type=row.account_type,
                normal_balance=row.normal_balance,
                total_debit=row.total_debit,
                total_credit=row.total_credit,
                net_debit=diff if diff > ZERO else ZERO,
                net_credit=-diff if diff < ZERO else ZERO,
            )
        )
    return TrialBalanceResponse(
        as_of_date=report.as_of_date,
        rows=rows,
        grand_total_debit=report.grand_total_debit,
        grand_total_credit=report.grand_total_credit,
        is_balanced=report.is_balanced,
    )
