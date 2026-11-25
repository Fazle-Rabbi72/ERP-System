"""Authentication HTTP router. Thin layer: no business logic here."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service, get_current_auth
from app.core.security import TokenPayload
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MfaDisableRequest,
    MfaEnableRequest,
    MfaSetupResponse,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    pair = await service.login(
        tenant_code=body.tenant_code,
        email=str(body.email),
        password=body.password,
        otp_code=body.otp_code,
    )
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    pair = await service.refresh(refresh_token=body.refresh_token)
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    auth: Annotated[TokenPayload, Depends(get_current_auth)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    body: LogoutRequest | None = None,
) -> None:
    await service.logout(
        access_payload=auth,
        refresh_token=body.refresh_token if body is not None else None,
    )


@router.get("/me", response_model=UserResponse)
async def me(
    auth: Annotated[TokenPayload, Depends(get_current_auth)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    user = await service.get_current_user(auth)
    return UserResponse.model_validate(user)


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(
    auth: Annotated[TokenPayload, Depends(get_current_auth)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MfaSetupResponse:
    data = await service.setup_mfa(auth)
    return MfaSetupResponse(secret=data.secret, otpauth_uri=data.otpauth_uri)


@router.post("/mfa/enable", response_model=UserResponse)
async def mfa_enable(
    body: MfaEnableRequest,
    auth: Annotated[TokenPayload, Depends(get_current_auth)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    user = await service.enable_mfa(auth, otp_code=body.otp_code)
    return UserResponse.model_validate(user)


@router.post("/mfa/disable", response_model=UserResponse)
async def mfa_disable(
    body: MfaDisableRequest,
    auth: Annotated[TokenPayload, Depends(get_current_auth)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    user = await service.disable_mfa(auth, password=body.password, otp_code=body.otp_code)
    return UserResponse.model_validate(user)
