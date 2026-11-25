import httpx
import pytest
from fastapi import FastAPI

from app.core.db import Database
from app.core.exceptions import ServiceUnavailableError
from app.main import create_app
from tests.factories import make_settings

pytestmark = pytest.mark.unit


class FakeDatabase(Database):
    def __init__(self, *, healthy: bool) -> None:
        self._healthy = healthy

    async def ping(self) -> bool:
        return self._healthy

    async def dispose(self) -> None:
        return None


class FakeRedis:
    pass


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_live_is_ok() -> None:
    async with _client(create_app(make_settings())) as client:
        response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_reports_degraded_with_503(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(make_settings())
    app.state.database = FakeDatabase(healthy=True)
    app.state.redis = object()
    monkeypatch.setattr("app.api.deps.Redis", FakeRedis)
    app.state.redis = FakeRedis()

    async def redis_down(_client: object) -> bool:
        return False

    monkeypatch.setattr("app.api.deps.ping_redis", redis_down)
    async with _client(app) as client:
        response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": True, "redis": False}


async def test_ready_ok_when_all_up(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(make_settings())
    app.state.database = FakeDatabase(healthy=True)
    app.state.redis = FakeRedis()
    monkeypatch.setattr("app.api.deps.Redis", FakeRedis)

    async def redis_up(_client: object) -> bool:
        return True

    monkeypatch.setattr("app.api.deps.ping_redis", redis_up)
    async with _client(app) as client:
        response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": True, "redis": True}


async def test_ready_fails_closed_when_state_missing() -> None:
    app = create_app(make_settings())
    # The central handler that maps this to a JSON 503 is added in F4; until then
    # the error must surface as ServiceUnavailableError rather than a fake "ok".
    async with _client(app) as client:
        with pytest.raises(ServiceUnavailableError):
            await client.get("/health/ready")


def test_docs_hidden_in_production() -> None:
    production = create_app(
        make_settings(app_env="production", jwt_secret_key="k" * 48, db_app_password="Str0ng-Pass")
    )
    development = create_app(make_settings())
    assert production.docs_url is None
    assert production.openapi_url is None
    assert development.docs_url == "/docs"


async def test_cors_allows_only_configured_origin() -> None:
    app = create_app(make_settings(cors_allowed_origins="http://good.test"))
    async with _client(app) as client:
        good = await client.get("/health/live", headers={"Origin": "http://good.test"})
        bad = await client.get("/health/live", headers={"Origin": "http://evil.test"})
    assert good.headers.get("access-control-allow-origin") == "http://good.test"
    assert "access-control-allow-origin" not in bad.headers


async def test_lifespan_sets_and_releases_resources() -> None:
    app = create_app(make_settings())
    async with app.router.lifespan_context(app):
        assert isinstance(app.state.database, Database)
        assert app.state.redis is not None
