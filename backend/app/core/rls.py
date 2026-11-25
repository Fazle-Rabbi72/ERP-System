"""Row-Level Security (RLS) SQL helpers for Alembic migrations.

Every tenant-scoped table gets:
1. `ENABLE ROW LEVEL SECURITY`
2. `FORCE ROW LEVEL SECURITY` (even table owners are subject unless they have BYPASSRLS)
3. A single uniform policy requiring
   `tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid`
   for both reading (`USING`) and writing (`WITH CHECK`).

When `app.tenant_id` is unset or empty, `NULLIF(..., '')` evaluates to NULL,
`tenant_id = NULL` is unknown (false), and the query fails closed (sees 0 rows
and refuses writes).
"""

import re

_IDENT_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")

TENANT_ISOLATION_EXPR = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def validate_identifier(name: str) -> str:
    """Ensure a PostgreSQL table/role identifier contains only safe characters."""
    if not _IDENT_RE.fullmatch(name):
        msg = f"Invalid PostgreSQL identifier: {name!r}"
        raise ValueError(msg)
    return name


def rls_policy_name(table_name: str) -> str:
    safe_table = validate_identifier(table_name)
    return f"tenant_isolation_{safe_table}"


def rls_enable_statements(table_name: str) -> tuple[str, ...]:
    """Return ordered SQL statements to enable and force tenant RLS on a table."""
    safe_table = validate_identifier(table_name)
    policy = rls_policy_name(safe_table)
    return (
        f'ALTER TABLE "{safe_table}" ENABLE ROW LEVEL SECURITY',
        f'ALTER TABLE "{safe_table}" FORCE ROW LEVEL SECURITY',
        f'DROP POLICY IF EXISTS "{policy}" ON "{safe_table}"',
        (
            f'CREATE POLICY "{policy}" ON "{safe_table}" '
            f"AS PERMISSIVE FOR ALL "
            f"USING ({TENANT_ISOLATION_EXPR}) "
            f"WITH CHECK ({TENANT_ISOLATION_EXPR})"
        ),
    )


def rls_disable_statements(table_name: str) -> tuple[str, ...]:
    """Return ordered SQL statements to remove tenant RLS on a table (for downgrade)."""
    safe_table = validate_identifier(table_name)
    policy = rls_policy_name(safe_table)
    return (
        f'DROP POLICY IF EXISTS "{policy}" ON "{safe_table}"',
        f'ALTER TABLE "{safe_table}" NO FORCE ROW LEVEL SECURITY',
        f'ALTER TABLE "{safe_table}" DISABLE ROW LEVEL SECURITY',
    )
