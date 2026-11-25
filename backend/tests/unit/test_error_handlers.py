"""Unit tests for centralized error handlers and RequestContextMiddleware."""

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.core.exceptions import ConflictError, NotFoundError
from app.main import create_app
from tests.factories import make_settings

pytestmark = pytest.mark.unit


class _SamplePayload(BaseModel):
    amount: int = Field(gt=0)
    secret_password: str = Field(min_length=8)


def _test_app() -> FastAPI:
    app = create_app(make_settings())

    @app.get("/_test/not-found")
    async def _raise_not_found() -> None:
        raise NotFoundError("Voucher missing", details={"voucher_no": "JV-001"})

    @app.get("/_test/conflict")
    async def _raise_conflict() -> None:
        raise ConflictError

    @app.post("/_test/validate")
    async def _validate(payload: _SamplePayload) -> dict[str, int]:
        return {"amount": payload.amount}

    @app.get("/_test/crash")
    async def _crash() -> None:
        msg = "SELECT * FROM secrets WHERE password='super-secret-value'"
        raise RuntimeError(msg)

    return app


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def test_app_error_uses_consistent_envelope_and_request_id() -> None:
    app = _test_app()
    async with _client(app) as client:
        res = await client.get("/_test/not-found", headers={"X-Request-ID": "req-123.abc"})
    assert res.status_code == 404
    assert res.headers["x-request-id"] == "req-123.abc"
    assert res.json() == {
        "error": {
            "code": "not_found",
            "message": "Voucher missing",
            "details": {"voucher_no": "JV-001"},
            "request_id": "req-123.abc",
        }
    }


async def test_unsafe_request_id_header_is_replaced_with_uuid() -> None:
    app = _test_app()
    async with _client(app) as client:
        res = await client.get("/_test/conflict", headers={"X-Request-ID": "bad\r\nheader value!"})
    assert res.status_code == 409
    req_id = res.headers["x-request-id"]
    assert "bad" not in req_id
    assert res.json()["error"]["request_id"] == req_id


async def test_validation_error_never_echoes_raw_input_values() -> None:
    app = _test_app()
    async with _client(app) as client:
        res = await client.post(
            "/_test/validate",
            json={"amount": -5, "secret_password": "s3cr3t!"},
        )
    assert res.status_code == 422
    text_body = res.text
    assert "s3cr3t!" not in text_body
    body = res.json()
    assert body["error"]["code"] == "validation_error"
    fields = {item["field"] for item in body["error"]["details"]["fields"]}
    assert fields == {"amount", "secret_password"}


async def test_unknown_route_and_method_not_allowed_use_error_envelope() -> None:
    app = _test_app()
    async with _client(app) as client:
        not_found = await client.get("/does-not-exist")
        wrong_method = await client.delete("/health/live")
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "not_found"
    assert wrong_method.status_code == 405
    assert wrong_method.json()["error"]["code"] == "method_not_allowed"


async def test_unhandled_exception_hides_stack_trace_and_internals() -> None:
    app = _test_app()
    async with _client(app) as client:
        res = await client.get("/_test/crash")
    assert res.status_code == 500
    assert "super-secret-value" not in res.text
    assert "RuntimeError" not in res.text
    assert "Traceback" not in res.text
    body = res.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert body["error"]["details"] == {}
    assert body["error"]["request_id"] == res.headers["x-request-id"]
