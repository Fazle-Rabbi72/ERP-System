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

# M3 Purchase & Supplier permission codes
PERM_PURCHASE_SUPPLIERS_READ = "purchase.suppliers.read"
PERM_PURCHASE_SUPPLIERS_WRITE = "purchase.suppliers.write"
PERM_PURCHASE_BILLS_READ = "purchase.bills.read"
PERM_PURCHASE_BILLS_WRITE = "purchase.bills.write"
PERM_PURCHASE_BILLS_POST = "purchase.bills.post"
PERM_PURCHASE_PAYMENTS_WRITE = "purchase.payments.write"

# M4 Inventory & Warehouse permission codes
PERM_INVENTORY_PRODUCTS_READ = "inventory.products.read"
PERM_INVENTORY_PRODUCTS_WRITE = "inventory.products.write"
PERM_INVENTORY_WAREHOUSES_READ = "inventory.warehouses.read"
PERM_INVENTORY_WAREHOUSES_WRITE = "inventory.warehouses.write"
PERM_INVENTORY_STOCK_READ = "inventory.stock.read"
PERM_INVENTORY_STOCK_MOVE = "inventory.stock.move"

# M5 VAT & Mushak permission codes
PERM_VAT_RATES_READ = "vat.rates.read"
PERM_VAT_RATES_WRITE = "vat.rates.write"
PERM_VAT_REPORTS_READ = "vat.reports.read"

# M6 HR & Payroll permission codes
PERM_HR_EMPLOYEES_READ = "hr.employees.read"
PERM_HR_EMPLOYEES_WRITE = "hr.employees.write"
PERM_HR_PAYROLL_READ = "hr.payroll.read"
PERM_HR_PAYROLL_WRITE = "hr.payroll.write"
PERM_HR_PAYROLL_POST = "hr.payroll.post"

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
    PermissionDef(PERM_PURCHASE_SUPPLIERS_READ, "purchase", "View suppliers"),
    PermissionDef(PERM_PURCHASE_SUPPLIERS_WRITE, "purchase", "Create and manage suppliers"),
    PermissionDef(PERM_PURCHASE_BILLS_READ, "purchase", "View purchase bills"),
    PermissionDef(PERM_PURCHASE_BILLS_WRITE, "purchase", "Create draft purchase bills"),
    PermissionDef(PERM_PURCHASE_BILLS_POST, "purchase", "Post purchase bills to GL"),
    PermissionDef(PERM_PURCHASE_PAYMENTS_WRITE, "purchase", "Record supplier payments"),
    PermissionDef(PERM_INVENTORY_PRODUCTS_READ, "inventory", "View products catalog"),
    PermissionDef(PERM_INVENTORY_PRODUCTS_WRITE, "inventory", "Create and manage products"),
    PermissionDef(PERM_INVENTORY_WAREHOUSES_READ, "inventory", "View warehouses"),
    PermissionDef(PERM_INVENTORY_WAREHOUSES_WRITE, "inventory", "Create and manage warehouses"),
    PermissionDef(PERM_INVENTORY_STOCK_READ, "inventory", "View stock levels and movements"),
    PermissionDef(PERM_INVENTORY_STOCK_MOVE, "inventory", "Record stock in/out/adjustment"),
    PermissionDef(PERM_VAT_RATES_READ, "vat", "View configurable VAT rate profiles"),
    PermissionDef(PERM_VAT_RATES_WRITE, "vat", "Create and manage VAT rate profiles"),
    PermissionDef(PERM_VAT_REPORTS_READ, "vat", "View Mushak 6.1, 6.2, 6.3 and 9.1 summaries"),
    PermissionDef(PERM_HR_EMPLOYEES_READ, "hr", "View employee directory and compensation"),
    PermissionDef(PERM_HR_EMPLOYEES_WRITE, "hr", "Create and manage employees"),
    PermissionDef(PERM_HR_PAYROLL_READ, "hr", "View monthly payroll runs and payslips"),
    PermissionDef(PERM_HR_PAYROLL_WRITE, "hr", "Generate draft monthly payroll runs"),
    PermissionDef(PERM_HR_PAYROLL_POST, "hr", "Post monthly payroll runs to General Ledger"),
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
            PERM_PURCHASE_SUPPLIERS_READ,
            PERM_PURCHASE_BILLS_READ,
            PERM_INVENTORY_PRODUCTS_READ,
            PERM_INVENTORY_WAREHOUSES_READ,
            PERM_INVENTORY_STOCK_READ,
            PERM_VAT_RATES_READ,
            PERM_VAT_REPORTS_READ,
            PERM_HR_EMPLOYEES_READ,
            PERM_HR_PAYROLL_READ,
        ),
    ),
    SystemRoleDef(
        code="viewer",
        name="Viewer",
        description="Basic read-only access.",
        permissions=(PERM_USERS_READ,),
    ),
)
