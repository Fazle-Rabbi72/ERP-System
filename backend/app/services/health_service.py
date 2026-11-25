"""Readiness checks for infrastructure dependencies."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

Probe = Callable[[], Awaitable[bool]]


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    database: bool
    redis: bool

    @property
    def is_ready(self) -> bool:
        return self.database and self.redis


class HealthService:
    def __init__(self, database_probe: Probe, redis_probe: Probe) -> None:
        self._database_probe = database_probe
        self._redis_probe = redis_probe

    async def check(self) -> ReadinessReport:
        return ReadinessReport(
            database=await self._database_probe(),
            redis=await self._redis_probe(),
        )
