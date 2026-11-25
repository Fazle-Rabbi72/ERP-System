"""Centralized exception handlers producing a single consistent JSON error format.

Stack traces, SQL queries, internal paths, and raw user inputs (which may
contain secrets) are NEVER exposed to clients.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError, JsonValue
from app.core.logging import get_logger
from app.schemas.common import ErrorDetail, ErrorResponse

logger = get_logger(__name__)

_HTTP_STATUS_CODES: dict[int, tuple[str, str]] = {
    400: ("bad_request", "The request is invalid."),
    401: ("authentication_failed", "Authentication is required or has failed."),
    403: ("permission_denied", "You do not have permission to perform this action."),
    404: ("not_found", "The requested resource was not found."),
    405: ("method_not_allowed", "This HTTP method is not allowed for the requested resource."),
    409: ("conflict", "The request conflicts with the current state of the resource."),
    422: ("validation_error", "The submitted data is not valid."),
    429: ("rate_limited", "Too many requests. Please try again later."),
    503: ("service_unavailable", "The service is temporarily unavailable."),
}


def _get_request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None


def _error_json(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, JsonValue] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details or {},
            request_id=request_id,
        )
    )
    headers = {"X-Request-ID": request_id} if request_id is not None else None
    return JSONResponse(status_code=status_code, content=payload.model_dump(), headers=headers)


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):
        return await _handle_unexpected_error(request, exc)
    request_id = _get_request_id(request)
    if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error("app_error", code=exc.code, status_code=exc.status_code)
    else:
        logger.warning("app_error", code=exc.code, status_code=exc.status_code)
    return _error_json(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=request_id,
    )


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return await _handle_unexpected_error(request, exc)
    request_id = _get_request_id(request)
    fields: list[JsonValue] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field_path = ".".join(str(part) for part in loc if part != "body")
        fields.append(
            {
                "field": field_path or "body",
                "message": str(err.get("msg", "Invalid value")),
                "type": str(err.get("type", "value_error")),
            }
        )
    logger.warning("request_validation_failed", error_count=len(fields))
    return _error_json(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation_error",
        message="The submitted data is not valid.",
        details={"fields": fields},
        request_id=request_id,
    )


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        return await _handle_unexpected_error(request, exc)
    request_id = _get_request_id(request)
    code, default_message = _HTTP_STATUS_CODES.get(
        exc.status_code,
        ("http_error", "The request could not be completed."),
    )
    if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error("http_exception", status_code=exc.status_code)
    else:
        logger.warning("http_exception", status_code=exc.status_code)
    return _error_json(
        status_code=exc.status_code,
        code=code,
        message=default_message,
        request_id=request_id,
    )


async def _handle_unexpected_error(request: Request, _exc: Exception) -> JSONResponse:
    request_id = _get_request_id(request)
    logger.exception("unhandled_exception")
    return _error_json(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="An unexpected error occurred.",
        request_id=request_id,
    )


def register_error_handlers(app: FastAPI) -> None:
    """Attach all centralized exception handlers to the FastAPI application."""
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)
