"""Test helpers. Settings are built from explicit values only: neither the real
.env nor OS environment variables may leak into unit tests."""

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from app.core.config import Settings


class IsolatedSettings(Settings):
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "db_app_password": "test-db-password",
        "jwt_secret_key": "test-jwt-secret-that-is-long-enough-0123456789",
    }
    values.update(overrides)
    return IsolatedSettings.model_validate(values)
