"""Add RBAC tables (roles, permissions, role_permissions, user_roles) with RLS.

Revision ID: 0003_rbac_tables
Revises: 0002_auth_users_and_tokens
Create Date: 2026-11-25 16:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.rls import rls_disable_statements, rls_enable_statements

revision: str = "0003_rbac_tables"
down_revision: str | None = "0002_auth_users_and_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _audit_columns() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=500), server_default="", nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_roles_tenant_code"),
    )
    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"], unique=False)
    op.create_index("ix_roles_is_deleted", "roles", ["is_deleted"], unique=False)
    op.create_index("ix_roles_code", "roles", ["code"], unique=False)

    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=500), server_default="", nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_permissions_tenant_code"),
    )
    op.create_index("ix_permissions_tenant_id", "permissions", ["tenant_id"], unique=False)
    op.create_index("ix_permissions_is_deleted", "permissions", ["is_deleted"], unique=False)
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=False)
    op.create_index("ix_permissions_module", "permissions", ["module"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_role_permissions_role_id_roles", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name="fk_role_permissions_permission_id_permissions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_role_permissions"),
        sa.UniqueConstraint(
            "tenant_id", "role_id", "permission_id", name="uq_role_permissions_tenant_role_perm"
        ),
    )
    op.create_index("ix_role_permissions_tenant_id", "role_permissions", ["tenant_id"])
    op.create_index("ix_role_permissions_is_deleted", "role_permissions", ["is_deleted"])
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_roles_user_id_users", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_user_roles_role_id_roles", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_roles"),
        sa.UniqueConstraint(
            "tenant_id", "user_id", "role_id", name="uq_user_roles_tenant_user_role"
        ),
    )
    op.create_index("ix_user_roles_tenant_id", "user_roles", ["tenant_id"])
    op.create_index("ix_user_roles_is_deleted", "user_roles", ["is_deleted"])
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    for table in ("roles", "permissions", "role_permissions", "user_roles"):
        for statement in rls_enable_statements(table):
            op.execute(statement)


def downgrade() -> None:
    for table in ("user_roles", "role_permissions", "permissions", "roles"):
        for statement in rls_disable_statements(table):
            op.execute(statement)
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
