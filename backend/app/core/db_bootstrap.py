"""Idempotent database role and privilege bootstrapper.

Works identically on local PostgreSQL 16 and hosted Neon PostgreSQL:
- Connects as `DB_ADMIN_USER` / `DB_ADMIN_PASSWORD` (only loaded here, never by
  the runtime web app).
- Creates/updates two least-privilege roles:
    1. `DB_MIGRATOR_USER` (owns tables created by Alembic, NOBYPASSRLS)
    2. `DB_APP_USER` (runtime app role: CRUD only, NOT table owner, NOBYPASSRLS)
- Sets default privileges so every future table created by the migrator is
  automatically accessible to the app role.
- Verifies that `DB_APP_USER` is neither a superuser nor `BYPASSRLS`.

Run with: `python -m app.core.db_bootstrap` (or `make db-bootstrap`).
"""

import asyncio
import sys

import asyncpg
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import ROOT_DIR, Settings, get_settings
from app.core.db import build_ssl_context
from app.core.rls import validate_identifier


class BootstrapSettings(BaseSettings):
    """Admin credentials used ONLY during one-time / idempotent DB bootstrap."""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        hide_input_in_errors=True,
    )

    db_admin_user: str
    db_admin_password: SecretStr


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


async def _ensure_role(
    conn: asyncpg.Connection,
    role_name: str,
    password: str,
) -> None:
    safe_role = validate_identifier(role_name)
    exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", safe_role)
    quoted_pw = _quote_literal(password)
    if exists:
        await conn.execute(
            f'ALTER ROLE "{safe_role}" WITH LOGIN NOSUPERUSER NOCREATEDB '
            f"NOCREATEROLE NOBYPASSRLS PASSWORD {quoted_pw}"
        )
    else:
        await conn.execute(
            f'CREATE ROLE "{safe_role}" WITH LOGIN NOSUPERUSER NOCREATEDB '
            f"NOCREATEROLE NOBYPASSRLS PASSWORD {quoted_pw}"
        )


async def bootstrap_database(
    settings: Settings | None = None,
    admin: BootstrapSettings | None = None,
) -> None:
    active = settings or get_settings()
    admin_cfg = admin or BootstrapSettings()  # pyright: ignore[reportCallIssue]

    if active.db_migrator_user is None or active.db_migrator_password is None:
        msg = "DB_MIGRATOR_USER and DB_MIGRATOR_PASSWORD must be set in .env"
        raise ValueError(msg)

    host = active.db_migrator_host or active.db_host
    db_name = validate_identifier(active.db_name)
    migrator = validate_identifier(active.db_migrator_user)
    app_user = validate_identifier(active.db_app_user)
    ssl_ctx = build_ssl_context(active.db_ssl_mode)

    conn = await asyncpg.connect(
        host=host,
        port=active.db_port,
        user=admin_cfg.db_admin_user,
        password=admin_cfg.db_admin_password.get_secret_value(),
        database=db_name,
        ssl=ssl_ctx,
        timeout=30,
    )
    try:
        await _ensure_role(conn, migrator, active.db_migrator_password.get_secret_value())
        await _ensure_role(conn, app_user, active.db_app_password.get_secret_value())

        # Grant membership to current admin so ALTER DEFAULT PRIVILEGES FOR ROLE works on PG 16+.
        current_user = str(await conn.fetchval("SELECT current_user"))
        if current_user != migrator:
            safe_current = validate_identifier(current_user)
            await conn.execute(f'GRANT "{migrator}" TO "{safe_current}"')

        await conn.execute(f'GRANT CONNECT ON DATABASE "{db_name}" TO "{migrator}", "{app_user}"')
        await conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        await conn.execute(f'GRANT USAGE, CREATE ON SCHEMA public TO "{migrator}"')
        await conn.execute(f'GRANT USAGE ON SCHEMA public TO "{app_user}"')

        await conn.execute(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE "{migrator}" IN SCHEMA public '
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{app_user}"'
        )
        await conn.execute(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE "{migrator}" IN SCHEMA public '
            f'GRANT USAGE, SELECT ON SEQUENCES TO "{app_user}"'
        )
        # Also cover tables/sequences that may already exist.
        await conn.execute(
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{app_user}"'
        )
        await conn.execute(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{app_user}"')

        # Verify least privilege on the runtime app role.
        row = await conn.fetchrow(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = $1",
            app_user,
        )
        if row is None or bool(row["rolsuper"]) or bool(row["rolbypassrls"]):
            msg = f"Role {app_user!r} must NOT be superuser or have BYPASSRLS"
            raise RuntimeError(msg)
    finally:
        await conn.close()


def main() -> None:
    asyncio.run(bootstrap_database())
    sys.stdout.write("[nexzen] Database roles and privileges bootstrapped successfully.\n")


if __name__ == "__main__":
    main()
