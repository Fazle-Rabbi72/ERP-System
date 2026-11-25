"""Pure ASGI middleware for request correlation IDs and structured log context."""

import re
import uuid
from typing import TYPE_CHECKING

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

if TYPE_CHECKING:
    from collections.abc import MutableMapping

REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _extract_or_generate_request_id(scope: Scope) -> str:
    raw_headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
    for name, value in raw_headers:
        if name.lower() == b"x-request-id":
            decoded = value.decode("latin-1", errors="ignore").strip()
            if _SAFE_REQUEST_ID_RE.fullmatch(decoded):
                return decoded
            break
    return str(uuid.uuid4())


class RequestContextMiddleware:
    """Attaches a safe `request_id` to every HTTP request, log line, and response."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_id = _extract_or_generate_request_id(scope)
        state: MutableMapping[str, object] = scope.setdefault("state", {})
        state["request_id"] = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=scope.get("method", ""),
            path=scope.get("path", ""),
        )

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                if not any(name.lower() == b"x-request-id" for name, _ in headers):
                    headers.append((b"x-request-id", request_id.encode("ascii")))
                    message["headers"] = headers
            await send(message)

        try:
            await self._app(scope, receive, send_with_request_id)
        finally:
            structlog.contextvars.clear_contextvars()
