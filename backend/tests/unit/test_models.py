"""Unit tests for SQLAlchemy base model invariants and MONEY_TYPE."""

import pytest
from sqlalchemy import Numeric

from app.models import MONEY_TYPE, Base, Tenant

pytestmark = pytest.mark.unit

REQUIRED_COLUMNS = {
    "id",
    "tenant_id",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "is_deleted",
}


def test_every_table_has_mandatory_columns() -> None:
    assert len(Base.metadata.tables) >= 1
    for table_name, table in Base.metadata.tables.items():
        missing = REQUIRED_COLUMNS - set(table.columns.keys())
        assert not missing, f"Table {table_name!r} is missing required columns: {missing}"


def test_money_type_is_numeric_18_2_decimal() -> None:
    assert isinstance(MONEY_TYPE, Numeric)
    assert MONEY_TYPE.precision == 18
    assert MONEY_TYPE.scale == 2
    assert MONEY_TYPE.asdecimal is True


def test_tenant_model_has_self_tenant_check_constraint() -> None:
    table = Base.metadata.tables[Tenant.__tablename__]
    constraint_names = {c.name for c in table.constraints}
    assert "ck_tenants_self_tenant_id" in constraint_names
