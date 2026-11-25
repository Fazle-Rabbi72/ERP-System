"""FastAPI dependencies shared by routers."""

from functools import partial
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis

from app.core.auth_store import AuthStore
from app.core.config import Settings
from app.core.db import Database
from app.core.exceptions import AuthenticationError, ServiceUnavailableError
from app.core.redis import ping_redis
from app.core.security import TokenPayload, decode_token
from app.services.auth_service import AuthService
from app.services.health_service import HealthService

_BEARER = HTTPBearer(auto_error=False)


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
