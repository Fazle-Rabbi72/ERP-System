import pytest

from app.core.exceptions import (
    AppError,
    AuthenticationError,
    BadRequestError,
    BusinessRuleError,
    ConflictError,
    DomainValidationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServiceUnavailableError,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("error_type", "status_code", "code"),
    [
        (AppError, 500, "internal_error"),
        (BadRequestError, 400, "bad_request"),
        (AuthenticationError, 401, "authentication_failed"),
        (PermissionDeniedError, 403, "permission_denied"),
        (NotFoundError, 404, "not_found"),
        (ConflictError, 409, "conflict"),
        (DomainValidationError, 422, "validation_error"),
        (BusinessRuleError, 422, "business_rule_violation"),
        (RateLimitError, 429, "rate_limited"),
        (ServiceUnavailableError, 503, "service_unavailable"),
    ],
)
def test_error_metadata(error_type: type[AppError], status_code: int, code: str) -> None:
    error = error_type()
    assert error.status_code == status_code
    assert error.code == code
    assert error.message == error_type.default_message
    assert error.details == {}


def test_custom_message_and_details() -> None:
    error = NotFoundError("Invoice not found", details={"id": "42", "tags": ["a", 1, None]})
    assert error.message == "Invoice not found"
    assert error.details["id"] == "42"
    assert str(error) == "Invoice not found"


def test_codes_are_unique_per_meaning() -> None:
    codes = [
        cls.code
        for cls in (
            AppError,
            BadRequestError,
            AuthenticationError,
            PermissionDeniedError,
            NotFoundError,
            ConflictError,
            DomainValidationError,
            BusinessRuleError,
            RateLimitError,
            ServiceUnavailableError,
        )
    ]
    assert len(codes) == len(set(codes))
