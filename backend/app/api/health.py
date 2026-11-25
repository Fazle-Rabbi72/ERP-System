"""Liveness and readiness endpoints for systemd, Nginx and load balancers.

These are the ONLY unauthenticated endpoints. They expose no tenant data and no
internals, only whether the process and its dependencies are up. They are
therefore a deliberate, documented exception to the auth/RBAC/audit rule.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_health_service
from app.schemas.health import LiveResponse, ReadyResponse
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LiveResponse)
async def live() -> LiveResponse:
    return LiveResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadyResponse}},
)
async def ready(
    response: Response,
    service: Annotated[HealthService, Depends(get_health_service)],
) -> ReadyResponse:
    report = await service.check()
    if not report.is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(
        status="ok" if report.is_ready else "degraded",
        database=report.database,
        redis=report.redis,
    )
