import ssl

import pytest
from redis.asyncio import SSLConnection
from redis.asyncio.connection import Connection

from app.core.db import build_ssl_context
from app.core.redis import create_redis
from tests.factories import make_settings

pytestmark = pytest.mark.unit


def test_ssl_disable_gives_no_context() -> None:
    assert build_ssl_context("disable") is None


def test_ssl_require_encrypts_without_verifying() -> None:
    context = build_ssl_context("require")
    assert context is not None
    assert context.verify_mode == ssl.CERT_NONE
    assert context.check_hostname is False


def test_ssl_verify_full_verifies_certificate_and_hostname() -> None:
    context = build_ssl_context("verify-full")
    assert context is not None
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


async def test_redis_uses_tls_pool_and_connection_cap_when_configured() -> None:
    client = create_redis(
        make_settings(
            redis_host="redis.example.com",
            redis_ssl=True,
            redis_password="p@ss:w/rd",
            redis_max_connections=7,
        )
    )
    try:
        pool = client.connection_pool
        assert pool.connection_class is SSLConnection
        assert pool.max_connections == 7
        assert pool.connection_kwargs["password"] == "p@ss:w/rd"
    finally:
        await client.aclose()


async def test_redis_plain_connection_by_default() -> None:
    client = create_redis(make_settings())
    try:
        assert client.connection_pool.connection_class is Connection
    finally:
        await client.aclose()
