"""Data-access layer (repositories). Called by services, never by routers directly."""

from app.repositories.base import BaseRepository
from app.repositories.tenant import TenantRepository

__all__ = ["BaseRepository", "TenantRepository"]
