"""Authentication service: login, refresh rotation, reuse detection, logout, optional MFA."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, text

from app.core.auth_store import AuthStore
from app.core.config import Settings
from app.core.db import Database
from app.core.exceptions import (
    AuthenticationError,
    BadRequestError,
    BusinessRuleError,
    NotFoundError,
    RateLimitError,
)
from app.core.logging import get_logger
from app.core.security import (
    TokenPayload,
    build_totp_uri,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    hash_password,
    needs_rehash,
    verify_dummy_password,
    verify_password,
    verify_totp,
)
from app.models.refresh_token import RefreshToken
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class MfaSetupData:
    secret: str
    otpauth_uri: str


class AuthService:
    """All authentication business logic lives here; routers only delegate."""

    def __init__(
        self,
        database: Database,
        auth_store: AuthStore,
        settings: Settings,
    ) -> None:
        self._database = database
        self._store = auth_store
        self._settings = settings

    async def _resolve_tenant_id(self, tenant_code: str | None) -> uuid.UUID:
        if self._settings.deployment_mode == "onprem":
            if self._settings.onprem_tenant_id is None:
                raise BadRequestError("On-premise tenant is not configured.")
            return self._settings.onprem_tenant_id

        if not tenant_code or not tenant_code.strip():
            raise BadRequestError("tenant_code is required in cloud mode.")

        cleaned = tenant_code.strip().lower()
        async with self._database.transaction(None) as session:
            await session.execute(
                text("SELECT set_config('app.lookup_tenant_code', :code, true)"),
                {"code": cleaned},
            )
            stmt = select(Tenant.id).where(
                Tenant.code == cleaned,
                Tenant.is_active.is_(True),
                Tenant.is_deleted.is_(False),
            )
            tenant_id = (await session.execute(stmt)).scalar_one_or_none()
        if tenant_id is None:
            raise AuthenticationError("Invalid credentials.")
        return tenant_id

    async def _mint_and_store_tokens(
        self,
        *,
        user: User,
        refresh_repo: RefreshTokenRepository,
        family_id: uuid.UUID | None = None,
    ) -> tuple[TokenPair, TokenPayload]:
        access_jwt, _access_payload = create_access_token(
            self._settings,
            user_id=user.id,
            tenant_id=user.tenant_id,
        )
        refresh_jwt, refresh_payload = create_refresh_token(
            self._settings,
            user_id=user.id,
            tenant_id=user.tenant_id,
            family_id=family_id,
        )
        if refresh_payload.family_id is None:
            raise AuthenticationError("Failed to create refresh token family.")
        await refresh_repo.create(
            RefreshToken(
                tenant_id=user.tenant_id,
                user_id=user.id,
                jti=refresh_payload.jti,
                family_id=refresh_payload.family_id,
                expires_at=refresh_payload.exp,
            ),
            actor_id=user.id,
        )
        pair = TokenPair(
            access_token=access_jwt,
            refresh_token=refresh_jwt,
            expires_in=self._settings.access_token_ttl_minutes * 60,
        )
        return pair, refresh_payload

    async def login(
        self,
        *,
        tenant_code: str | None,
        email: str,
        password: str,
        otp_code: str | None = None,
    ) -> TokenPair:
        normalised_email = email.strip().lower()
        try:
            tenant_id = await self._resolve_tenant_id(tenant_code)
        except AuthenticationError:
            verify_dummy_password(password)
            raise

        if await self._store.is_locked_out(tenant_id, normalised_email):
            logger.warning("login_locked_out", tenant_id=str(tenant_id))
            raise RateLimitError("Too many failed login attempts. Account temporarily locked.")

        async with self._database.transaction(tenant_id) as session:
            user_repo = UserRepository(session, tenant_id)
            refresh_repo = RefreshTokenRepository(session, tenant_id)
            user = await user_repo.get_by_email(normalised_email)

            if user is None or not user.is_active:
                verify_dummy_password(password)
                await self._store.record_failed_attempt(tenant_id, normalised_email)
                logger.warning(
                    "login_failed", tenant_id=str(tenant_id), reason="unknown_or_inactive"
                )
                raise AuthenticationError("Invalid credentials.")

            if not verify_password(password, user.password_hash):
                await self._store.record_failed_attempt(tenant_id, normalised_email)
                logger.warning(
                    "login_failed",
                    tenant_id=str(tenant_id),
                    user_id=str(user.id),
                    reason="bad_password",
                )
                raise AuthenticationError("Invalid credentials.")

            if user.mfa_enabled and (
                not otp_code or not user.mfa_secret or not verify_totp(user.mfa_secret, otp_code)
            ):
                await self._store.record_failed_attempt(tenant_id, normalised_email)
                logger.warning(
                    "login_failed",
                    tenant_id=str(tenant_id),
                    user_id=str(user.id),
                    reason="bad_mfa",
                )
                raise AuthenticationError("Invalid or missing MFA code.")

            if needs_rehash(user.password_hash):
                user.password_hash = hash_password(password)
            user.last_login_at = datetime.now(UTC)
            await user_repo.update(user, actor_id=user.id)

            pair, _ = await self._mint_and_store_tokens(user=user, refresh_repo=refresh_repo)

        await self._store.clear_failed_attempts(tenant_id, normalised_email)
        logger.info("login_succeeded", tenant_id=str(tenant_id), user_id=str(user.id))
        return pair

    async def refresh(self, *, refresh_token: str) -> TokenPair:
        payload = decode_token(self._settings, refresh_token, expected_type="refresh")
        if payload.family_id is None:
            raise AuthenticationError("Invalid refresh token.")

        reuse_detected = False
        async with self._database.transaction(payload.tenant_id) as session:
            refresh_repo = RefreshTokenRepository(session, payload.tenant_id)
            user_repo = UserRepository(session, payload.tenant_id)

            stored = await refresh_repo.get_by_jti(payload.jti)
            if stored is None or stored.revoked_at is not None:
                # Possible stolen/replayed refresh token: revoke the entire family!
                await refresh_repo.revoke_family(payload.family_id, actor_id=payload.sub)
                reuse_detected = True
            else:
                if stored.expires_at <= datetime.now(UTC):
                    raise AuthenticationError("Refresh token has expired.")

                user = await user_repo.get_by_id(payload.sub)
                if user is None or not user.is_active:
                    await refresh_repo.revoke_family(payload.family_id, actor_id=payload.sub)
                    raise AuthenticationError("Account is no longer active.")

                pair, new_payload = await self._mint_and_store_tokens(
                    user=user,
                    refresh_repo=refresh_repo,
                    family_id=payload.family_id,
                )
                await refresh_repo.revoke_jti(
                    payload.jti,
                    replaced_by_jti=new_payload.jti,
                    actor_id=user.id,
                )

        if reuse_detected:
            logger.warning(
                "refresh_token_reuse_detected",
                tenant_id=str(payload.tenant_id),
                user_id=str(payload.sub),
                family_id=str(payload.family_id),
            )
            raise AuthenticationError("Refresh token has been revoked.")

        logger.info(
            "token_refreshed",
            tenant_id=str(payload.tenant_id),
            user_id=str(payload.sub),
        )
        return pair

    async def logout(
        self,
        *,
        access_payload: TokenPayload,
        refresh_token: str | None = None,
    ) -> None:
        await self._store.revoke_access_token(
            access_payload.jti,
            access_payload.remaining_ttl_seconds,
        )
        if refresh_token is not None:
            try:
                refresh_payload = decode_token(
                    self._settings,
                    refresh_token,
                    expected_type="refresh",
                )
            except AuthenticationError:
                refresh_payload = None
            if (
                refresh_payload is not None
                and refresh_payload.family_id is not None
                and refresh_payload.sub == access_payload.sub
                and refresh_payload.tenant_id == access_payload.tenant_id
            ):
                async with self._database.transaction(access_payload.tenant_id) as session:
                    refresh_repo = RefreshTokenRepository(session, access_payload.tenant_id)
                    await refresh_repo.revoke_family(
                        refresh_payload.family_id,
                        actor_id=access_payload.sub,
                    )
        logger.info(
            "logout_succeeded",
            tenant_id=str(access_payload.tenant_id),
            user_id=str(access_payload.sub),
        )

    async def get_current_user(self, payload: TokenPayload) -> User:
        async with self._database.transaction(payload.tenant_id) as session:
            user = await UserRepository(session, payload.tenant_id).get_by_id(payload.sub)
            if user is None or not user.is_active:
                raise AuthenticationError("Account is not active.")
            return user

    async def setup_mfa(self, payload: TokenPayload) -> MfaSetupData:
        secret = generate_totp_secret()
        async with self._database.transaction(payload.tenant_id) as session:
            user_repo = UserRepository(session, payload.tenant_id)
            user = await user_repo.get_by_id(payload.sub)
            if user is None:
                raise NotFoundError("User not found.")
            if user.mfa_enabled:
                raise BusinessRuleError("MFA is already enabled for this account.")
            user.mfa_secret = secret
            await user_repo.update(user, actor_id=user.id)
            uri = build_totp_uri(secret, email=user.email)
        return MfaSetupData(secret=secret, otpauth_uri=uri)

    async def enable_mfa(self, payload: TokenPayload, *, otp_code: str) -> User:
        async with self._database.transaction(payload.tenant_id) as session:
            user_repo = UserRepository(session, payload.tenant_id)
            user = await user_repo.get_by_id(payload.sub)
            if user is None:
                raise NotFoundError("User not found.")
            if not user.mfa_secret:
                raise BusinessRuleError("Run MFA setup before enabling MFA.")
            if not verify_totp(user.mfa_secret, otp_code):
                raise AuthenticationError("Invalid MFA verification code.")
            user.mfa_enabled = True
            updated = await user_repo.update(user, actor_id=user.id)
        logger.info("mfa_enabled", tenant_id=str(payload.tenant_id), user_id=str(payload.sub))
        return updated

    async def disable_mfa(
        self,
        payload: TokenPayload,
        *,
        password: str,
        otp_code: str,
    ) -> User:
        async with self._database.transaction(payload.tenant_id) as session:
            user_repo = UserRepository(session, payload.tenant_id)
            user = await user_repo.get_by_id(payload.sub)
            if user is None:
                raise NotFoundError("User not found.")
            if not user.mfa_enabled or not user.mfa_secret:
                raise BusinessRuleError("MFA is not enabled for this account.")
            if not verify_password(password, user.password_hash):
                raise AuthenticationError("Invalid password.")
            if not verify_totp(user.mfa_secret, otp_code):
                raise AuthenticationError("Invalid MFA verification code.")
            user.mfa_enabled = False
            user.mfa_secret = None
            updated = await user_repo.update(user, actor_id=user.id)
        logger.info("mfa_disabled", tenant_id=str(payload.tenant_id), user_id=str(payload.sub))
        return updated
