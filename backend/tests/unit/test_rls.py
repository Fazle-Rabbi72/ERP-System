"""Unit tests for Row-Level Security SQL helpers."""

import pytest

from app.core.rls import (
    TENANT_ISOLATION_EXPR,
    rls_disable_statements,
    rls_enable_statements,
    rls_policy_name,
    validate_identifier,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("name", ["tenants", "journal_entries", "vat_mushak_6_3"])
def test_validate_identifier_accepts_safe_names(name: str) -> None:
    assert validate_identifier(name) == name


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "Tenants",
        "1invalid",
        "tenants; DROP TABLE users;--",
        'tenants" CASCADE',
        "a" * 64,
    ],
)
def test_validate_identifier_rejects_unsafe_names(bad: str) -> None:
    with pytest.raises(ValueError, match="Invalid PostgreSQL identifier"):
        validate_identifier(bad)


def test_rls_enable_statements_force_and_isolate() -> None:
    stmts = rls_enable_statements("tenants")
    assert stmts[0] == 'ALTER TABLE "tenants" ENABLE ROW LEVEL SECURITY'
    assert stmts[1] == 'ALTER TABLE "tenants" FORCE ROW LEVEL SECURITY'
    assert f'"{rls_policy_name("tenants")}"' in stmts[3]
    assert f"USING ({TENANT_ISOLATION_EXPR})" in stmts[3]
    assert f"WITH CHECK ({TENANT_ISOLATION_EXPR})" in stmts[3]


def test_rls_disable_statements_clean_up() -> None:
    stmts = rls_disable_statements("tenants")
    assert len(stmts) == 3
    assert "DROP POLICY IF EXISTS" in stmts[0]
    assert "NO FORCE ROW LEVEL SECURITY" in stmts[1]
    assert "DISABLE ROW LEVEL SECURITY" in stmts[2]
