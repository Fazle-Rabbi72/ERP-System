"""Redis client factory and health probe."""

from urllib.parse import quote

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_redis(settings: Settings) -> Redis:
    """Create a lazy async client (no connection is made until first use).

    `rediss://` (TLS) is used when REDIS_SSL=true, as required by hosted Redis.
    The pool is capped by REDIS_MAX_CONNECTIONS because free hosted plans limit
    concurrent connections.
    """
    scheme = "rediss" if settings.redis_ssl else "redis"
    credentials = ""
    if settings.redis_password is not None:
        credentials = f":{quote(settings.redis_password.get_secret_value(), safe='')}@"
    url = f"{scheme}://{credentials}{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    client: Redis = Redis.from_url(
        url,
        decode_responses=True,
        max_connections=settings.redis_max_connections,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )
    return client


async def ping_redis(client: Redis) -> bool:
    """True if Redis answers PING. Never raises."""
    try:
        await client.ping()
    except (RedisError, OSError, TimeoutError):
        logger.warning("redis_ping_failed")
        return False
    return True
