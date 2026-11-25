"""Application exceptions.

`message` is shown to end users, so it must never contain stack traces, SQL,
file paths or secrets. The central handler that turns these into the JSON error
format is added in step F4.
"""

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None


class AppError(Exception):
    """Base class for all errors that are safe to report to the client."""

    status_code: int = 500
    code: str = "internal_error"
    default_message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, JsonValue] | None = None,
    ) -> None:
        self.message: str = message or self.default_message
        self.details: dict[str, JsonValue] = details or {}
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"
    default_message = "The request is invalid."


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_failed"
    default_message = "Authentication is required or has failed."


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"
    default_message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    default_message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    default_message = "The request conflicts with the current state of the resource."


class DomainValidationError(AppError):
    status_code = 422
    code = "validation_error"
    default_message = "The submitted data is not valid."


class BusinessRuleError(AppError):
    status_code = 422
    code = "business_rule_violation"
    default_message = "The operation violates a business rule."


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"
    default_message = "Too many requests. Please try again later."


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
    default_message = "The service is temporarily unavailable."
