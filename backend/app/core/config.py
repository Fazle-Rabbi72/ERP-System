"""Application configuration, loaded only from environment variables / .env.

No secret has a default value. In production the app refuses to start when a
secret is still the template placeholder or obviously weak.
"""

import uuid
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import URL

ROOT_DIR = Path(__file__).resolve().parents[3]
PLACEHOLDER = "CHANGE_ME"
MIN_PRODUCTION_JWT_SECRET_LENGTH = 32


def _is_loopback(host: str) -> bool:
    return host.strip().lower() in {"localhost", "127.0.0.1", "::1"}


class Settings(BaseSettings):
    """Typed settings. Field names map to upper-case environment variables."""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        # Never echo input values (which may be secrets) in validation errors.
        hide_input_in_errors=True,
    )

    # --- General ---
    app_env: Literal["development", "test", "production"] = "development"
    deployment_mode: Literal["cloud", "onprem"] = "cloud"
    onprem_tenant_id: uuid.UUID | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_prefix: str = "/api/v1"
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # --- PostgreSQL ---
    db_host: str = "localhost"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "nexzen_erp"
    db_app_user: str = "nexzen_app"
    db_app_password: SecretStr
    db_migrator_host: str | None = None  # direct (non-pooled) host for migrations
    db_migrator_user: str | None = None
    db_migrator_password: SecretStr | None = None
    db_ssl_mode: Literal["disable", "require", "verify-full"] = "disable"
    db_statement_cache_size: int = Field(default=100, ge=0, le=10_000)
    db_pool_recycle_seconds: int = Field(default=300, ge=30, le=3600)
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=10, ge=0, le=100)
    db_pool_timeout_seconds: int = Field(default=30, ge=1, le=300)
    db_statement_timeout_ms: int = Field(default=30_000, ge=100, le=600_000)

    # --- Redis ---
    redis_host: str = "localhost"
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_db: int = Field(default=0, ge=0, le=15)
    redis_password: SecretStr | None = None
    redis_ssl: bool = False
    redis_max_connections: int = Field(default=10, ge=1, le=1000)

    # --- Background Worker (ARQ) ---
    arq_poll_delay_seconds: float = Field(default=2.0, ge=0.2, le=60.0)
    arq_max_jobs: int = Field(default=10, ge=1, le=100)

    # --- Security ---
    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_ttl_days: int = Field(default=7, ge=1, le=90)
    login_max_attempts: int = Field(default=5, ge=3, le=20)
    login_lockout_minutes: int = Field(default=15, ge=1, le=1440)

    @field_validator("app_env", "deployment_mode", mode="before")
    @classmethod
    def _normalise_lower(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_upper(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator(
        "onprem_tenant_id",
        "redis_password",
        "db_migrator_host",
        "db_migrator_user",
        "db_migrator_password",
        mode="before",
    )
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip().rstrip("/") for part in value.split(",") if part.strip()]
        return value

    @field_validator("api_prefix")
    @classmethod
    def _check_prefix(cls, value: str) -> str:
        if not value.startswith("/") or (len(value) > 1 and value.endswith("/")):
            msg = "API_PREFIX must start with '/' and must not end with '/'"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _check_cross_field_rules(self) -> Self:
        if self.deployment_mode == "onprem" and self.onprem_tenant_id is None:
            msg = "ONPREM_TENANT_ID is required when DEPLOYMENT_MODE=onprem"
            raise ValueError(msg)
        if self.db_migrator_user is not None and self.db_migrator_password is None:
            msg = "DB_MIGRATOR_PASSWORD is required when DB_MIGRATOR_USER is set"
            raise ValueError(msg)
        if self.app_env == "production":
            problems = self._production_problems()
            if problems:
                raise ValueError("; ".join(problems))
        return self

    def _production_problems(self) -> list[str]:
        """Describe unsafe production settings. Never includes secret values."""
        problems: list[str] = []
        secrets: dict[str, SecretStr | None] = {
            "JWT_SECRET_KEY": self.jwt_secret_key,
            "DB_APP_PASSWORD": self.db_app_password,
            "DB_MIGRATOR_PASSWORD": self.db_migrator_password,
        }
        for name, secret in secrets.items():
            if secret is not None and PLACEHOLDER in secret.get_secret_value():
                problems.append(f"{name} still contains the placeholder {PLACEHOLDER}")
        if len(self.jwt_secret_key.get_secret_value()) < MIN_PRODUCTION_JWT_SECRET_LENGTH:
            problems.append(
                f"JWT_SECRET_KEY must be at least {MIN_PRODUCTION_JWT_SECRET_LENGTH} characters"
            )
        if self.db_ssl_mode == "disable" and not _is_loopback(self.db_host):
            problems.append("DB_SSL_MODE must not be 'disable' for a non-local database host")
        if not _is_loopback(self.redis_host):
            if not self.redis_ssl:
                problems.append("REDIS_SSL must be true for a non-local Redis host")
            if self.redis_password is None:
                problems.append("REDIS_PASSWORD is required for a non-local Redis host")
        if "*" in self.cors_allowed_origins:
            problems.append("CORS_ALLOWED_ORIGINS must not contain '*' in production")
        return problems

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def database_url(self) -> URL:
        """Runtime (non-owner, RLS-subject) connection URL. Password is masked in str()."""
        return self._postgres_url(self.db_host, self.db_app_user, self.db_app_password)

    @property
    def migrator_database_url(self) -> URL:
        """Privileged URL used only by Alembic migrations."""
        if self.db_migrator_user is None or self.db_migrator_password is None:
            msg = "DB_MIGRATOR_USER and DB_MIGRATOR_PASSWORD must be set to run migrations"
            raise ValueError(msg)
        host = self.db_migrator_host or self.db_host
        return self._postgres_url(host, self.db_migrator_user, self.db_migrator_password)

    def _postgres_url(self, host: str, user: str, password: SecretStr) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=user,
            password=password.get_secret_value(),
            host=host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings, read once from the environment."""
    return Settings()  # pyright: ignore[reportCallIssue]
