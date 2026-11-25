"""Pydantic request and response schemas for authentication endpoints."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    tenant_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=64,
        description="Required in cloud mode; omitted in on-premise mode.",
    )
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    otp_code: str | None = Field(default=None, min_length=6, max_length=8)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=16, max_length=2048)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=16, max_length=2048)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = Field(default="bearer")
    expires_in: int = Field(description="Access token lifetime in seconds")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    mfa_enabled: bool
    last_login_at: datetime | None


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class MfaEnableRequest(BaseModel):
    otp_code: str = Field(min_length=6, max_length=8)


class MfaDisableRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    otp_code: str = Field(min_length=6, max_length=8)
