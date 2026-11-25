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

# M1 Accounting & General Ledger permission codes
PERM_ACCOUNTING_ACCOUNTS_READ = "accounting.accounts.read"
PERM_ACCOUNTING_ACCOUNTS_WRITE = "accounting.accounts.write"
PERM_ACCOUNTING_JOURNALS_READ = "accounting.journals.read"
PERM_ACCOUNTING_JOURNALS_WRITE = "accounting.journals.write"
PERM_ACCOUNTING_JOURNALS_POST = "accounting.journals.post"
PERM_ACCOUNTING_REPORTS_READ = "accounting.reports.read"

# M2 Sales & Invoicing permission codes
PERM_SALES_CUSTOMERS_READ = "sales.customers.read"
PERM_SALES_CUSTOMERS_WRITE = "sales.customers.write"
PERM_SALES_INVOICES_READ = "sales.invoices.read"
PERM_SALES_INVOICES_WRITE = "sales.invoices.write"
PERM_SALES_INVOICES_POST = "sales.invoices.post"
PERM_SALES_PAYMENTS_WRITE = "sales.payments.write"

BASELINE_PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef(PERM_RBAC_ROLES_READ, "rbac", "View roles and permissions"),
    PermissionDef(PERM_RBAC_ROLES_WRITE, "rbac", "Create and modify roles"),
    PermissionDef(PERM_RBAC_USERS_ASSIGN, "rbac", "Assign or revoke roles for users"),
    PermissionDef(PERM_USERS_READ, "users", "View users in the organisation"),
    PermissionDef(PERM_USERS_WRITE, "users", "Create and manage users"),
    PermissionDef(PERM_AUDIT_READ, "audit", "View immutable audit logs"),
    PermissionDef(PERM_ACCOUNTING_ACCOUNTS_READ, "accounting", "View Chart of Accounts"),
    PermissionDef(PERM_ACCOUNTING_ACCOUNTS_WRITE, "accounting", "Create and edit accounts"),
    PermissionDef(PERM_ACCOUNTING_JOURNALS_READ, "accounting", "View journal vouchers"),
    PermissionDef(PERM_ACCOUNTING_JOURNALS_WRITE, "accounting", "Create draft journal vouchers"),
    PermissionDef(PERM_ACCOUNTING_JOURNALS_POST, "accounting", "Post or reverse journal vouchers"),
    PermissionDef(PERM_ACCOUNTING_REPORTS_READ, "accounting", "View Trial Balance & GL reports"),
    PermissionDef(PERM_SALES_CUSTOMERS_READ, "sales", "View customers"),
    PermissionDef(PERM_SALES_CUSTOMERS_WRITE, "sales", "Create and manage customers"),
    PermissionDef(PERM_SALES_INVOICES_READ, "sales", "View sales invoices"),
    PermissionDef(PERM_SALES_INVOICES_WRITE, "sales", "Create draft sales invoices"),
    PermissionDef(PERM_SALES_INVOICES_POST, "sales", "Post sales invoices to GL"),
    PermissionDef(PERM_SALES_PAYMENTS_WRITE, "sales", "Record customer payments"),
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
        description="Read-only access to roles, users, accounting reports, and audit logs.",
        permissions=(
            PERM_RBAC_ROLES_READ,
            PERM_USERS_READ,
            PERM_AUDIT_READ,
            PERM_ACCOUNTING_ACCOUNTS_READ,
            PERM_ACCOUNTING_JOURNALS_READ,
            PERM_ACCOUNTING_REPORTS_READ,
            PERM_SALES_CUSTOMERS_READ,
            PERM_SALES_INVOICES_READ,
        ),
    ),
    SystemRoleDef(
        code="viewer",
        name="Viewer",
        description="Basic read-only access.",
        permissions=(PERM_USERS_READ,),
    ),
)
