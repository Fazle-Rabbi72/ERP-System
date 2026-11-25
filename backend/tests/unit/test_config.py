import uuid

import pytest
from pydantic import ValidationError

from app.core.config import ROOT_DIR, Settings
from tests.factories import make_settings

pytestmark = pytest.mark.unit

STRONG = {
    "app_env": "production",
    "jwt_secret_key": "k" * 48,
    "db_app_password": "Str0ng-App-Pass",
}


def test_defaults_and_cors_parsing() -> None:
    settings = make_settings(cors_allowed_origins="http://a.test/, http://b.test ,")
    assert settings.app_env == "development"
    assert settings.deployment_mode == "cloud"
    assert settings.cors_allowed_origins == ["http://a.test", "http://b.test"]


def test_onprem_requires_tenant_id() -> None:
    with pytest.raises(ValidationError):
        make_settings(deployment_mode="onprem")
    tenant = uuid.uuid4()
    settings = make_settings(deployment_mode="onprem", onprem_tenant_id=str(tenant))
    assert settings.onprem_tenant_id == tenant


def test_blank_optional_values_become_none() -> None:
    settings = make_settings(onprem_tenant_id="", redis_password="  ")
    assert settings.onprem_tenant_id is None
    assert settings.redis_password is None


def test_production_rejects_placeholder_secrets() -> None:
    with pytest.raises(ValidationError) as excinfo:
        make_settings(**{**STRONG, "db_app_password": "CHANGE_ME"})
    assert "DB_APP_PASSWORD" in str(excinfo.value)


def test_production_rejects_weak_jwt_secret_without_leaking_it() -> None:
    with pytest.raises(ValidationError) as excinfo:
        make_settings(**{**STRONG, "jwt_secret_key": "short-secret"})
    rendered = str(excinfo.value)
    assert "at least 32" in rendered
    assert "short-secret" not in rendered


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        make_settings(**STRONG, cors_allowed_origins="*")


def test_production_accepts_strong_configuration() -> None:
    settings = make_settings(**STRONG, cors_allowed_origins="https://erp.example.com")
    assert settings.is_production


def test_migrator_user_requires_password() -> None:
    with pytest.raises(ValidationError):
        make_settings(db_migrator_user="nexzen_migrator")


def test_migrator_url_requires_credentials() -> None:
    with pytest.raises(ValueError, match="DB_MIGRATOR"):
        _ = make_settings().migrator_database_url
    settings = make_settings(db_migrator_user="mig", db_migrator_password="pw")
    assert settings.migrator_database_url.username == "mig"


def test_database_url_masks_password() -> None:
    url = make_settings(db_app_password="p@ss/word").database_url
    assert "p@ss/word" not in str(url)
    assert url.password == "p@ss/word"
    assert url.drivername == "postgresql+asyncpg"


def test_secrets_are_masked_in_repr() -> None:
    assert "test-db-password" not in repr(make_settings())


def test_invalid_api_prefix_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(api_prefix="api/v1/")


def test_env_example_file_is_loadable() -> None:
    settings = Settings(_env_file=ROOT_DIR / ".env.example")
    assert settings.deployment_mode == "cloud"
    assert settings.onprem_tenant_id is None
    assert settings.cors_allowed_origins == ["http://localhost:5173"]


def test_production_requires_tls_for_remote_database_and_redis() -> None:
    with pytest.raises(ValidationError) as excinfo:
        make_settings(**STRONG, db_host="ep-x.neon.tech", redis_host="r.example.com")
    rendered = str(excinfo.value)
    assert "DB_SSL_MODE" in rendered
    assert "REDIS_SSL" in rendered
    assert "REDIS_PASSWORD" in rendered


def test_production_accepts_remote_services_with_tls() -> None:
    settings = make_settings(
        **STRONG,
        db_host="ep-x.neon.tech",
        db_ssl_mode="verify-full",
        redis_host="r.example.com",
        redis_ssl=True,
        redis_password="redis-pass",
    )
    assert settings.db_ssl_mode == "verify-full"


def test_migrator_url_uses_direct_host_when_given() -> None:
    settings = make_settings(
        db_host="ep-x-pooler.neon.tech",
        db_migrator_host="ep-x.neon.tech",
        db_migrator_user="mig",
        db_migrator_password="pw",
    )
    assert settings.database_url.host == "ep-x-pooler.neon.tech"
    assert settings.migrator_database_url.host == "ep-x.neon.tech"
