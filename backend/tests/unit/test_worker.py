"""Unit tests for ARQ worker settings and tasks."""

import pytest

from app.workers.settings import build_arq_redis_settings
from app.workers.tasks import ping_worker
from tests.factories import make_settings

pytestmark = pytest.mark.unit


def test_build_arq_redis_settings_maps_plain_and_tls() -> None:
    plain = build_arq_redis_settings(make_settings())
    assert plain.host == "localhost"
    assert plain.port == 6379
    assert plain.ssl is False
    assert plain.password is None

    tls = build_arq_redis_settings(
        make_settings(
            redis_host="redis.example.com",
            redis_port=16379,
            redis_db=2,
            redis_password="secret",
            redis_ssl=True,
        )
    )
    assert tls.host == "redis.example.com"
    assert tls.port == 16379
    assert tls.database == 2
    assert tls.password == "secret"
    assert tls.ssl is True


async def test_ping_worker_returns_ok_and_timestamp() -> None:
    result = await ping_worker({})
    assert result["status"] == "ok"
    assert "T" in result["timestamp"]
