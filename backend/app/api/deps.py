"""FastAPI dependencies shared by routers."""

from functools import partial

from fastapi import Request
from redis.asyncio import Redis

from app.core.db import Database
from app.core.exceptions import ServiceUnavailableError
from app.core.redis import ping_redis
from app.services.health_service import HealthService


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
