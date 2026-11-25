"""Redis-backed auth state: login lockout tracking and access-token revocation."""

import uuid

from redis.asyncio import Redis

from app.core.config import Settings


class AuthStore:
    """Stores ephemeral security state in Redis with strict TTLs."""

    def __init__(self, redis: Redis, settings: Settings) -> None:
        self._redis = redis
        self._max_attempts = settings.login_max_attempts
        self._lockout_seconds = settings.login_lockout_minutes * 60

    @staticmethod
    def _attempt_key(tenant_id: uuid.UUID, email: str) -> str:
        return f"nexzen:auth:fail:{tenant_id}:{email.strip().lower()}"

    @staticmethod
    def _revoked_jti_key(jti: uuid.UUID) -> str:
        return f"nexzen:auth:revoked:{jti}"

    async def is_locked_out(self, tenant_id: uuid.UUID, email: str) -> bool:
        raw = await self._redis.get(self._attempt_key(tenant_id, email))
        if raw is None:
            return False
        try:
            return int(raw) >= self._max_attempts
        except ValueError:
            return False

    async def record_failed_attempt(self, tenant_id: uuid.UUID, email: str) -> int:
        key = self._attempt_key(tenant_id, email)
        attempts = int(await self._redis.incr(key))
        await self._redis.expire(key, self._lockout_seconds)
        return attempts

    async def clear_failed_attempts(self, tenant_id: uuid.UUID, email: str) -> None:
        await self._redis.delete(self._attempt_key(tenant_id, email))

    async def revoke_access_token(self, jti: uuid.UUID, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        await self._redis.set(self._revoked_jti_key(jti), "1", ex=ttl_seconds)

    async def is_access_token_revoked(self, jti: uuid.UUID) -> bool:
        return bool(await self._redis.exists(self._revoked_jti_key(jti)))
