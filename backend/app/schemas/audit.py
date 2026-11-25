"""Pydantic response schemas for immutable audit logs."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    before_data: dict[str, object] | None
    after_data: dict[str, object] | None
    request_id: str | None
    ip_address: str | None
    created_at: datetime

