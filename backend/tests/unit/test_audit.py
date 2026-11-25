"""Unit tests for audit payload sanitization and append-only repository contract."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.logging import REDACTED
from app.repositories.audit_log import AuditLogRepository
from app.services.audit_service import sanitize_audit_payload

pytestmark = pytest.mark.unit


def test_sanitize_audit_payload_redacts_secrets_and_converts_domain_types() -> None:
    uid = uuid.uuid4()
    ts = datetime(2026, 11, 25, 10, 0, 0, tzinfo=UTC)
    payload: dict[str, object] = {
        "id": uid,
        "amount": Decimal("125000.50"),
        "created_at": ts,
        "password_hash": "$argon2id$secret",
        "nested": {
            "mfa_secret": "TOPSECRETBASE32",
            "refresh_token": "jwt-token",
            "safe_note": "Voucher approved",
        },
    }
    cleaned = sanitize_audit_payload(payload)
    assert cleaned is not None
    assert cleaned["id"] == str(uid)
    assert cleaned["amount"] == "125000.50"
    assert cleaned["created_at"] == ts.isoformat()
    assert cleaned["password_hash"] == REDACTED
    assert cleaned["nested"] == {
        "mfa_secret": REDACTED,
        "refresh_token": REDACTED,
        "safe_note": "Voucher approved",
    }


def test_sanitize_audit_payload_handles_none() -> None:
    assert sanitize_audit_payload(None) is None


def test_audit_repository_is_strictly_append_only() -> None:
    assert hasattr(AuditLogRepository, "append")
    assert not hasattr(AuditLogRepository, "update")
    assert not hasattr(AuditLogRepository, "soft_delete")
    assert not hasattr(AuditLogRepository, "delete")
