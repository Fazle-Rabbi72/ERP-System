"""FastAPI dependencies shared by routers."""

from collections.abc import Awaitable, Callable
from functools import partial
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis

from app.core.auth_store import AuthStore
from app.core.config import Settings
from app.core.db import Database
from app.core.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
    ServiceUnavailableError,
)
from app.core.logging import get_logger
from app.core.redis import ping_redis
from app.core.security import TokenPayload, decode_token
from app.services.accounting_service import AccountingService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.health_service import HealthService
from app.services.inventory_service import InventoryService
from app.services.purchase_service import PurchaseService
from app.services.rbac_service import RbacService
from app.services.sales_service import SalesService
from app.services.vat_service import VatService

_BEARER = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


def get_settings_from_request(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise ServiceUnavailableError
    return settings


def get_database(request: Request) -> Database:
    database = getattr(request.app.state, "database", None)
    if not isinstance(database, Database):
        raise ServiceUnavailableError
    return database


def get_redis(request: Request) -> Redis:
    client = getattr(request.app.state, "redis", None)
    if not isinstance(client, Redis):
        raise ServiceUnavailableError
    return client


def get_health_service(request: Request) -> HealthService:
    database = get_database(request)
    client = get_redis(request)
    return HealthService(database.ping, partial(ping_redis, client))


def get_auth_store(request: Request) -> AuthStore:
    return AuthStore(get_redis(request), get_settings_from_request(request))


def get_auth_service(request: Request) -> AuthService:
    return AuthService(
        database=get_database(request),
        auth_store=get_auth_store(request),
        settings=get_settings_from_request(request),
    )


def get_rbac_service(request: Request) -> RbacService:
    return RbacService(database=get_database(request))


def get_audit_service(request: Request) -> AuditService:
    return AuditService(database=get_database(request))


def get_accounting_service(request: Request) -> AccountingService:
    return AccountingService(database=get_database(request))


def get_sales_service(request: Request) -> SalesService:
    return SalesService(database=get_database(request))


def get_purchase_service(request: Request) -> PurchaseService:
    return PurchaseService(database=get_database(request))


def get_inventory_service(request: Request) -> InventoryService:
    return InventoryService(database=get_database(request))


def get_vat_service(request: Request) -> VatService:
    return VatService(database=get_database(request))


async def get_current_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_BEARER)],
    settings: Annotated[Settings, Depends(get_settings_from_request)],
    auth_store: Annotated[AuthStore, Depends(get_auth_store)],
) -> TokenPayload:
    """Validate Bearer access JWT and verify it has not been revoked in Redis."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Missing bearer token.")
    payload = decode_token(settings, credentials.credentials, expected_type="access")
    if await auth_store.is_access_token_revoked(payload.jti):
        raise AuthenticationError("Token has been revoked.")
    return payload


def require_permission(
    *required_permissions: str,
) -> Callable[
    [TokenPayload, RbacService],
    Awaitable[TokenPayload],
]:
    """FastAPI dependency factory: enforces authentication + all listed RBAC permissions."""

    async def _checker(
        auth: Annotated[TokenPayload, Depends(get_current_auth)],
        rbac: Annotated[RbacService, Depends(get_rbac_service)],
    ) -> TokenPayload:
        allowed = await rbac.user_has_permissions(
            auth.tenant_id,
            auth.sub,
            required_permissions,
        )
        if not allowed:
            logger.warning(
                "permission_denied",
                tenant_id=str(auth.tenant_id),
                user_id=str(auth.sub),
                required=list(required_permissions),
            )
            raise PermissionDeniedError
        return auth

    return _checker
