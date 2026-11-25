"""RBAC ORM models: Role, Permission, RolePermission, UserRole (all tenant-scoped)."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBaseModel


class Role(TenantBaseModel):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_roles_tenant_code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", server_default=""
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )


class Permission(TenantBaseModel):
    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_permissions_tenant_code"),)

    code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", server_default=""
    )


class RolePermission(TenantBaseModel):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "role_id",
            "permission_id",
            name="uq_role_permissions_tenant_role_perm",
        ),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )


class UserRole(TenantBaseModel):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "role_id",
            name="uq_user_roles_tenant_user_role",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
