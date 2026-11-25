"""Canonical permission codes and baseline system roles.

Every protected endpoint declares its required permission(s) using these
constants so permission strings are never duplicated or typo-prone.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PermissionDef:
    code: str
    module: str
    description: str


# Foundation permission codes
PERM_RBAC_ROLES_READ = "rbac.roles.read"
PERM_RBAC_ROLES_WRITE = "rbac.roles.write"
PERM_RBAC_USERS_ASSIGN = "rbac.users.assign"
PERM_USERS_READ = "users.read"
PERM_USERS_WRITE = "users.write"
PERM_AUDIT_READ = "audit.read"

BASELINE_PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef(PERM_RBAC_ROLES_READ, "rbac", "View roles and permissions"),
    PermissionDef(PERM_RBAC_ROLES_WRITE, "rbac", "Create and modify roles"),
    PermissionDef(PERM_RBAC_USERS_ASSIGN, "rbac", "Assign or revoke roles for users"),
    PermissionDef(PERM_USERS_READ, "users", "View users in the organisation"),
    PermissionDef(PERM_USERS_WRITE, "users", "Create and manage users"),
    PermissionDef(PERM_AUDIT_READ, "audit", "View immutable audit logs"),
)

ALL_BASELINE_CODES: tuple[str, ...] = tuple(p.code for p in BASELINE_PERMISSIONS)


@dataclass(frozen=True, slots=True)
class SystemRoleDef:
    code: str
    name: str
    description: str
    permissions: tuple[str, ...]


BASELINE_ROLES: tuple[SystemRoleDef, ...] = (
    SystemRoleDef(
        code="tenant_admin",
        name="Tenant Administrator",
        description="Full administrative access within this company.",
        permissions=ALL_BASELINE_CODES,
    ),
    SystemRoleDef(
        code="auditor",
        name="Auditor",
        description="Read-only access to roles, users, and audit logs.",
        permissions=(PERM_RBAC_ROLES_READ, PERM_USERS_READ, PERM_AUDIT_READ),
    ),
    SystemRoleDef(
        code="viewer",
        name="Viewer",
        description="Basic read-only access.",
        permissions=(PERM_USERS_READ,),
    ),
)
