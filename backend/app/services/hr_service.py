"""HR & Payroll service with configurable allowances, PF, AIT and atomic GL posting."""

import calendar
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
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
from app.models.accounting import JournalEntry, JournalLine
from app.models.hr import Employee, PayrollLine, PayrollRun
from app.repositories.accounting import AccountRepository, JournalEntryRepository
from app.repositories.hr import (
    EmployeeRepository,
    PayrollLineRepository,
    PayrollRunRepository,
)
from app.services.audit_service import record_audit

ZERO = Decimal("0.00")
HUNDRED = Decimal("100")
TWO_PLACES = Decimal("0.01")

PAYROLL_ADVISORY_NOTE = (
    "Payroll figures use tenant-configured salary, PF, and monthly tax settings. "
    "Please verify Bangladesh Labour Act compliance, Provident Fund trust rules, "
    "and NBR salary AIT/TDS slabs with your HR & tax advisor before final filing."
)


@dataclass(frozen=True, slots=True)
class ComputedPayslip:
    basic_salary: Decimal
    allowances_total: Decimal
    gross_salary: Decimal
    pf_deduction: Decimal
    tax_deduction: Decimal
    other_deduction: Decimal
    total_deductions: Decimal
    net_salary: Decimal


def compute_payslip(
    *,
    basic_salary: Decimal,
    house_rent_allowance: Decimal = ZERO,
    medical_allowance: Decimal = ZERO,
    conveyance_allowance: Decimal = ZERO,
    other_allowance: Decimal = ZERO,
    pf_deduction_percent: Decimal = ZERO,
    tax_deduction_amount: Decimal = ZERO,
    other_deduction: Decimal = ZERO,
) -> ComputedPayslip:
    """Compute exact Decimal payslip breakdown using ROUND_HALF_UP."""
    basic = basic_salary.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    allowances = (
        house_rent_allowance + medical_allowance + conveyance_allowance + other_allowance
    ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    gross = (basic + allowances).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    pf = (basic * pf_deduction_percent / HUNDRED).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    tax = tax_deduction_amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    other_ded = other_deduction.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    total_ded = (pf + tax + other_ded).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    net = (gross - total_ded).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    if net < ZERO:
        raise BusinessRuleError("Total deductions cannot exceed gross salary.")
    return ComputedPayslip(
        basic_salary=basic,
        allowances_total=allowances,
        gross_salary=gross,
        pf_deduction=pf,
        tax_deduction=tax,
        other_deduction=other_ded,
        total_deductions=total_ded,
        net_salary=net,
    )


class HrService:
    """All HR & Payroll business logic lives here."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def list_employees(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        search: str | None = None,
    ) -> tuple[list[Employee], int]:
        order_by = build_order_by(
            sort,
            allowed={
                "employee_code": Employee.employee_code,
                "full_name": Employee.full_name,
                "join_date": Employee.join_date,
                "created_at": Employee.created_at,
            },
            default=[Employee.employee_code.asc()],
        )
        filters = build_filters([FilterRule(Employee.full_name, "ilike", search)] if search else [])
        async with self._database.transaction(tenant_id) as session:
            repo = EmployeeRepository(session, tenant_id)
            return await repo.list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                order_by=order_by,
                filters=filters,
            )

    async def create_employee(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        employee_code: str,
        full_name: str,
        designation: str,
        department: str,
        email: str,
        phone: str,
        nid_no: str,
        tin_no: str,
        join_date: date,
        basic_salary: Decimal,
        house_rent_allowance: Decimal,
        medical_allowance: Decimal,
        conveyance_allowance: Decimal,
        other_allowance: Decimal,
        pf_deduction_percent: Decimal,
        tax_deduction_amount: Decimal,
    ) -> Employee:
        normalized_code = employee_code.strip().upper()
        compute_payslip(
            basic_salary=basic_salary,
            house_rent_allowance=house_rent_allowance,
            medical_allowance=medical_allowance,
            conveyance_allowance=conveyance_allowance,
            other_allowance=other_allowance,
            pf_deduction_percent=pf_deduction_percent,
            tax_deduction_amount=tax_deduction_amount,
        )
        async with self._database.transaction(tenant_id) as session:
            repo = EmployeeRepository(session, tenant_id)
            if await repo.get_by_code(normalized_code) is not None:
                raise ConflictError(f"Employee code '{normalized_code}' already exists.")
            emp = await repo.create(
                Employee(
                    tenant_id=tenant_id,
                    employee_code=normalized_code,
                    full_name=full_name.strip(),
                    designation=designation.strip(),
                    department=department.strip(),
                    email=email.strip(),
                    phone=phone.strip(),
                    nid_no=nid_no.strip(),
                    tin_no=tin_no.strip(),
                    join_date=join_date,
                    basic_salary=basic_salary,
                    house_rent_allowance=house_rent_allowance,
                    medical_allowance=medical_allowance,
                    conveyance_allowance=conveyance_allowance,
                    other_allowance=other_allowance,
                    pf_deduction_percent=pf_deduction_percent,
                    tax_deduction_amount=tax_deduction_amount,
                    is_active=True,
                ),
                actor_id=actor_id,
            )
            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="hr.employee.created",
                resource_type="employee",
                resource_id=emp.id,
                after_data={"employee_code": emp.employee_code, "full_name": emp.full_name},
            )
            return emp

    async def list_payroll_runs(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
    ) -> tuple[list[PayrollRun], int]:
        order_by = build_order_by(
            sort,
            allowed={
                "run_no": PayrollRun.run_no,
                "pay_year": PayrollRun.pay_year,
                "pay_month": PayrollRun.pay_month,
                "created_at": PayrollRun.created_at,
            },
            default=[PayrollRun.created_at.desc()],
        )
        async with self._database.transaction(tenant_id) as session:
            repo = PayrollRunRepository(session, tenant_id)
            return await repo.list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                order_by=order_by,
            )

    async def create_payroll_run(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        pay_year: int,
        pay_month: int,
        notes: str,
    ) -> tuple[PayrollRun, list[tuple[PayrollLine, Employee]]]:
        async with self._database.transaction(tenant_id) as session:
            run_repo = PayrollRunRepository(session, tenant_id)
            if await run_repo.get_by_period(pay_year, pay_month) is not None:
                raise ConflictError(f"Payroll run for {pay_year}-{pay_month:02d} already exists.")

            emp_repo = EmployeeRepository(session, tenant_id)
            active_employees = await emp_repo.list_active()
            if not active_employees:
                raise BusinessRuleError("At least one active employee is required to run payroll.")

            run_no = f"PAY-{pay_year}-{pay_month:02d}"
            run = await run_repo.create(
                PayrollRun(
                    tenant_id=tenant_id,
                    run_no=run_no,
                    pay_year=pay_year,
                    pay_month=pay_month,
                    status="draft",
                    total_gross=ZERO,
                    total_deductions=ZERO,
                    total_net_pay=ZERO,
                    notes=notes.strip(),
                ),
                actor_id=actor_id,
            )

            line_repo = PayrollLineRepository(session, tenant_id)
            total_gross = ZERO
            total_deductions = ZERO
            total_net = ZERO
            created_pairs: list[tuple[PayrollLine, Employee]] = []

            for emp in active_employees:
                slip = compute_payslip(
                    basic_salary=emp.basic_salary,
                    house_rent_allowance=emp.house_rent_allowance,
                    medical_allowance=emp.medical_allowance,
                    conveyance_allowance=emp.conveyance_allowance,
                    other_allowance=emp.other_allowance,
                    pf_deduction_percent=emp.pf_deduction_percent,
                    tax_deduction_amount=emp.tax_deduction_amount,
                )
                line = await line_repo.create(
                    PayrollLine(
                        tenant_id=tenant_id,
                        payroll_run_id=run.id,
                        employee_id=emp.id,
                        basic_salary=slip.basic_salary,
                        allowances_total=slip.allowances_total,
                        gross_salary=slip.gross_salary,
                        pf_deduction=slip.pf_deduction,
                        tax_deduction=slip.tax_deduction,
                        other_deduction=slip.other_deduction,
                        total_deductions=slip.total_deductions,
                        net_salary=slip.net_salary,
                    ),
                    actor_id=actor_id,
                )
                total_gross += slip.gross_salary
                total_deductions += slip.total_deductions
                total_net += slip.net_salary
                created_pairs.append((line, emp))

            run.total_gross = total_gross.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            run.total_deductions = total_deductions.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            run.total_net_pay = total_net.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            await session.flush()

            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="hr.payroll.created",
                resource_type="payroll_run",
                resource_id=run.id,
                after_data={
                    "run_no": run.run_no,
                    "employee_count": len(created_pairs),
                    "total_net_pay": run.total_net_pay,
                },
            )
            return run, created_pairs

    async def get_payroll_run_detail(
        self,
        *,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> tuple[PayrollRun, list[tuple[PayrollLine, Employee]]]:
        async with self._database.transaction(tenant_id) as session:
            run = await PayrollRunRepository(session, tenant_id).get_by_id(run_id)
            if run is None:
                raise NotFoundError("Payroll run not found.")
            lines = await PayrollLineRepository(session, tenant_id).list_for_run_with_employees(
                run.id
            )
            return run, lines

    async def post_payroll_run(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        run_id: uuid.UUID,
        salary_expense_account_id: uuid.UUID,
        payment_account_id: uuid.UUID,
        deductions_payable_account_id: uuid.UUID | None = None,
    ) -> PayrollRun:
        async with self._database.transaction(tenant_id) as session:
            run_repo = PayrollRunRepository(session, tenant_id)
            run = await run_repo.get_by_id(run_id)
            if run is None:
                raise NotFoundError("Payroll run not found.")
            if run.status != "draft":
                raise BusinessRuleError("Only draft payroll runs can be posted to GL.")
            if run.total_gross <= ZERO:
                raise BusinessRuleError("Cannot post a zero-value payroll run.")
            if run.total_deductions > ZERO and deductions_payable_account_id is None:
                raise BusinessRuleError(
                    "Deductions payable account is required when payroll has PF/Tax deductions."
                )

            acc_repo = AccountRepository(session, tenant_id)
            expense_acc = await acc_repo.get_by_id(salary_expense_account_id)
            payment_acc = await acc_repo.get_by_id(payment_account_id)
            if expense_acc is None or not expense_acc.is_active or expense_acc.is_group:
                raise BusinessRuleError("Salary expense account must be an active ledger account.")
            if payment_acc is None or not payment_acc.is_active or payment_acc.is_group:
                raise BusinessRuleError("Payment account must be an active ledger account.")

            ded_acc = None
            if run.total_deductions > ZERO and deductions_payable_account_id is not None:
                ded_acc = await acc_repo.get_by_id(deductions_payable_account_id)
                if ded_acc is None or not ded_acc.is_active or ded_acc.is_group:
                    raise BusinessRuleError(
                        "Deductions payable account must be an active ledger account."
                    )

            last_day = calendar.monthrange(run.pay_year, run.pay_month)[1]
            posting_date = date(run.pay_year, run.pay_month, last_day)
            now = datetime.now(UTC)

            journal_repo = JournalEntryRepository(session, tenant_id)
            seq = await journal_repo.next_voucher_sequence(posting_date.year)
            voucher_no = f"JV-{posting_date.year}-{seq:06d}"
            entry = await journal_repo.create(
                JournalEntry(
                    tenant_id=tenant_id,
                    voucher_no=voucher_no,
                    entry_date=posting_date,
                    reference=run.run_no,
                    narration=f"Monthly Payroll {run.run_no} ({run.pay_year}-{run.pay_month:02d})",
                    status="posted",
                    posted_at=now,
                    posted_by=actor_id,
                ),
                actor_id=actor_id,
            )

            journal_lines = [
                JournalLine(
                    tenant_id=tenant_id,
                    journal_entry_id=entry.id,
                    account_id=expense_acc.id,
                    line_no=1,
                    description=f"Gross Salary Expense — {run.run_no}",
                    debit=run.total_gross,
                    credit=ZERO,
                    created_by=actor_id,
                    updated_by=actor_id,
                ),
                JournalLine(
                    tenant_id=tenant_id,
                    journal_entry_id=entry.id,
                    account_id=payment_acc.id,
                    line_no=2,
                    description=f"Net Salary Disbursement — {run.run_no}",
                    debit=ZERO,
                    credit=run.total_net_pay,
                    created_by=actor_id,
                    updated_by=actor_id,
                ),
            ]
            if run.total_deductions > ZERO and ded_acc is not None:
                journal_lines.append(
                    JournalLine(
                        tenant_id=tenant_id,
                        journal_entry_id=entry.id,
                        account_id=ded_acc.id,
                        line_no=3,
                        description=f"PF & Tax Deductions Payable — {run.run_no}",
                        debit=ZERO,
                        credit=run.total_deductions,
                        created_by=actor_id,
                        updated_by=actor_id,
                    )
                )

            session.add_all(journal_lines)
            run.status = "posted"
            run.journal_entry_id = entry.id
            run.posted_at = now
            run.posted_by = actor_id
            run.updated_by = actor_id
            await session.flush()

            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="hr.payroll.posted",
                resource_type="payroll_run",
                resource_id=run.id,
                after_data={
                    "run_no": run.run_no,
                    "journal_entry_id": str(entry.id),
                    "total_gross": run.total_gross,
                    "total_net_pay": run.total_net_pay,
                },
            )
            return run
