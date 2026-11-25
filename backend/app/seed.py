"""Idempotent baseline seeder: initial tenant, permissions, system roles, and admin user.

All seed values come from environment variables (`SEED_*`). No secret is ever
hardcoded. Run via `make seed` or `python -m app.seed`.
"""

import asyncio
import sys
import uuid

from pydantic import EmailStr, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select, text

from app.core.config import PLACEHOLDER, ROOT_DIR, Settings, get_settings
from app.core.db import Database
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.rbac import RoleRepository
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository
from app.services.rbac_service import seed_tenant_rbac

MIN_SEED_PASSWORD_LENGTH = 12


class SeedSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        hide_input_in_errors=True,
    )

    seed_tenant_code: str = Field(default="nexzen-demo", min_length=2, max_length=64)
    seed_tenant_name: str = Field(default="Nexzen Solution Ltd.", min_length=2, max_length=255)
    seed_admin_email: EmailStr = "admin@nexzen.com"
    seed_admin_name: str = Field(default="System Administrator", min_length=2, max_length=255)
    seed_admin_password: SecretStr


async def run_seed(
    settings: Settings | None = None,
    seed_cfg: SeedSettings | None = None,
) -> uuid.UUID:
    active = settings or get_settings()
    cfg = seed_cfg or SeedSettings()  # pyright: ignore[reportCallIssue]

    raw_pw = cfg.seed_admin_password.get_secret_value()
    if PLACEHOLDER in raw_pw or len(raw_pw) < MIN_SEED_PASSWORD_LENGTH:
        msg = "SEED_ADMIN_PASSWORD must be at least 12 characters and not CHANGE_ME."
        raise ValueError(msg)

    code = cfg.seed_tenant_code.strip().lower()
    db = Database(active)
    try:
        # Check if the tenant already exists by code (using the SELECT-only lookup policy).
        existing_tenant_id: uuid.UUID | None = None
        async with db.transaction(None) as session:
            await session.execute(
                text("SELECT set_config('app.lookup_tenant_code', :code, true)"),
                {"code": code},
            )
            existing_tenant_id = (
                await session.execute(select(Tenant.id).where(Tenant.code == code))
            ).scalar_one_or_none()

        tenant_id = existing_tenant_id or active.onprem_tenant_id or uuid.uuid4()

        async with db.transaction(tenant_id) as session:
            tenant_repo = TenantRepository(session, tenant_id)
            if await tenant_repo.get_by_id(tenant_id) is None:
                await tenant_repo.create(
                    Tenant(
                        id=tenant_id,
                        tenant_id=tenant_id,
                        code=code,
                        name=cfg.seed_tenant_name.strip(),
                    )
                )

            roles = await seed_tenant_rbac(session, tenant_id)

            user_repo = UserRepository(session, tenant_id)
            admin_email = str(cfg.seed_admin_email).strip().lower()
            admin = await user_repo.get_by_email(admin_email)
            if admin is None:
                admin = await user_repo.create(
                    User(
                        tenant_id=tenant_id,
                        email=admin_email,
                        full_name=cfg.seed_admin_name.strip(),
                        password_hash=hash_password(raw_pw),
                    )
                )

            await RoleRepository(session, tenant_id).assign_to_user(
                admin.id,
                roles["tenant_admin"].id,
                actor_id=admin.id,
            )
        return tenant_id
    finally:
        await db.dispose()


def main() -> None:
    tenant_id = asyncio.run(run_seed())
    sys.stdout.write(f"[nexzen] Seed complete for tenant {tenant_id}.\n")


if __name__ == "__main__":
    main()
