"""Pydantic schemas for RBAC roles, permissions, and assignments."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    module: str
    description: str


class RoleCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=2, max_length=128)
    description: str = Field(default="", max_length=500)
    permission_codes: list[str] = Field(default_factory=list)


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str
    is_system: bool
    created_at: datetime


class EffectivePermissionsResponse(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    permissions: list[str]
