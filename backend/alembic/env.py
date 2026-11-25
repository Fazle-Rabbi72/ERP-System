"""Async Alembic environment.

Connects using `Settings.migrator_database_url` (direct host, migrator role,
configured TLS) so migrations own the schema and `nexzen_app` remains subject
to Row-Level Security.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Import all models here so Base.metadata sees every table for autogenerate.
from app.core.config import get_settings
from app.core.db import build_ssl_context
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    settings = get_settings()
    context.configure(
        url=settings.migrator_database_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    settings = get_settings()
    connect_args: dict[str, object] = {}
    ssl_ctx = build_ssl_context(settings.db_ssl_mode)
    if ssl_ctx is not None:
        connect_args["ssl"] = ssl_ctx

    engine = create_async_engine(
        settings.migrator_database_url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_do_run_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
