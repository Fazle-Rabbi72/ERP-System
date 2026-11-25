"""Repositories for HR & Payroll (Employee, PayrollRun, PayrollLine)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hr import Employee, PayrollLine, PayrollRun
from app.repositories.base import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, Employee)

    async def get_by_code(self, employee_code: str) -> Employee | None:
        stmt = self._base_query().where(Employee.employee_code == employee_code)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Employee]:
        stmt = (
            self._base_query()
            .where(Employee.is_active.is_(True))
            .order_by(Employee.employee_code.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class PayrollRunRepository(BaseRepository[PayrollRun]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, PayrollRun)

    async def get_by_period(self, pay_year: int, pay_month: int) -> PayrollRun | None:
        stmt = self._base_query().where(
            PayrollRun.pay_year == pay_year,
            PayrollRun.pay_month == pay_month,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class PayrollLineRepository(BaseRepository[PayrollLine]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, PayrollLine)

    async def list_for_run_with_employees(
        self, payroll_run_id: uuid.UUID
    ) -> list[tuple[PayrollLine, Employee]]:
        stmt = (
            select(PayrollLine, Employee)
            .join(Employee, Employee.id == PayrollLine.employee_id)
            .where(
                PayrollLine.tenant_id == self._tenant_id,
                PayrollLine.is_deleted.is_(False),
                PayrollLine.payroll_run_id == payroll_run_id,
            )
            .order_by(Employee.employee_code.asc())
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
