"""Unit tests for RBAC permission catalog and `require_permission` dependency."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.api.deps import require_permission
from app.core.exceptions import PermissionDeniedError
from app.core.permissions import (
    ALL_BASELINE_CODES,
    BASELINE_PERMISSIONS,
    BASELINE_ROLES,
    PERM_RBAC_ROLES_READ,
    PERM_RBAC_ROLES_WRITE,
)
from app.core.security import TokenPayload
from app.services.rbac_service import RbacService

pytestmark = pytest.mark.unit


def _token_payload() -> TokenPayload:
    now = datetime.now(UTC)
    return TokenPayload(
        sub=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        jti=uuid.uuid4(),
        token_type="access",
        iat=now,
        exp=now + timedelta(minutes=15),
    )


def test_baseline_permissions_are_unique_and_referenced_validly() -> None:
    codes = [p.code for p in BASELINE_PERMISSIONS]
    assert len(codes) == len(set(codes))
    code_set = set(ALL_BASELINE_CODES)
    for role in BASELINE_ROLES:
        assert set(role.permissions).issubset(code_set)


async def test_require_permission_allows_authorized_user() -> None:
    auth = _token_payload()
    rbac = AsyncMock(spec=RbacService)
    rbac.user_has_permissions.return_value = True

    checker = require_permission(PERM_RBAC_ROLES_READ, PERM_RBAC_ROLES_WRITE)
    result = await checker(auth, rbac)

    assert result == auth
    rbac.user_has_permissions.assert_awaited_once_with(
        auth.tenant_id,
        auth.sub,
        (PERM_RBAC_ROLES_READ, PERM_RBAC_ROLES_WRITE),
    )


async def test_require_permission_denies_unauthorized_user() -> None:
    auth = _token_payload()
    rbac = AsyncMock(spec=RbacService)
    rbac.user_has_permissions.return_value = False

    checker = require_permission(PERM_RBAC_ROLES_WRITE)
    with pytest.raises(PermissionDeniedError):
        await checker(auth, rbac)
