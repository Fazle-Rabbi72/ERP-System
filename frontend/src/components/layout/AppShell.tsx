import {
  Banknote,
  BarChart3,
  BookOpen,
  Building2,
  FileCheck2,
  FileSpreadsheet,
  IdCard,
  Languages,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  Receipt,
  Scale,
  ShieldAlert,
  ShoppingCart,
  Truck,
  Users,
  Warehouse,
  X,
} from "lucide-react";
import * as React from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/features/auth/store";
import { cn } from "@/lib/cn";

interface NavItem {
  to: string;
  labelKey: string;
  icon: React.ComponentType<{ className?: string }>;
  permission?: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", labelKey: "nav.dashboard", icon: LayoutDashboard },
  {
    to: "/accounting/accounts",
    labelKey: "nav.accounts",
    icon: BookOpen,
    permission: "accounting.accounts.read",
  },
  {
    to: "/accounting/journals",
    labelKey: "nav.journals",
    icon: FileSpreadsheet,
    permission: "accounting.journals.read",
  },
  {
    to: "/accounting/trial-balance",
    labelKey: "nav.trialBalance",
    icon: Scale,
    permission: "accounting.reports.read",
  },
  {
    to: "/reports/statements",
    labelKey: "nav.financialStatements",
    icon: BarChart3,
    permission: "accounting.reports.read",
  },
  {
    to: "/sales/customers",
    labelKey: "nav.customers",
    icon: Users,
    permission: "sales.customers.read",
  },
  {
    to: "/sales/invoices",
    labelKey: "nav.invoices",
    icon: Receipt,
    permission: "sales.invoices.read",
  },
  {
    to: "/purchase/suppliers",
    labelKey: "nav.suppliers",
    icon: Truck,
    permission: "purchase.suppliers.read",
  },
  {
    to: "/purchase/bills",
    labelKey: "nav.bills",
    icon: ShoppingCart,
    permission: "purchase.bills.read",
  },
  {
    to: "/inventory/catalog",
    labelKey: "nav.catalog",
    icon: Package,
    permission: "inventory.products.read",
  },
  {
    to: "/inventory/stock",
    labelKey: "nav.stock",
    icon: Warehouse,
    permission: "inventory.stock.read",
  },
  {
    to: "/vat/mushak",
    labelKey: "nav.vatMushak",
    icon: FileCheck2,
    permission: "vat.reports.read",
  },
  {
    to: "/hr/employees",
    labelKey: "nav.employees",
    icon: IdCard,
    permission: "hr.employees.read",
  },
  {
    to: "/hr/payroll",
    labelKey: "nav.payroll",
    icon: Banknote,
    permission: "hr.payroll.read",
  },
  {
    to: "/audit-logs",
    labelKey: "nav.auditLogs",
    icon: ShieldAlert,
    permission: "audit.read",
  },
];

export function AppShell(): React.JSX.Element {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const permissions = useAuthStore((s) => s.permissions);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);
  const toggleBanglaDigits = useAuthStore((s) => s.toggleBanglaDigits);
  const logout = useAuthStore((s) => s.logout);
  const [mobileOpen, setMobileOpen] = React.useState(false);

  const visibleNav = NAV_ITEMS.filter(
    (item) => !item.permission || permissions.includes(item.permission),
  );

  const toggleLanguage = (): void => {
    void i18n.changeLanguage(i18n.language === "bn" ? "en" : "bn");
  };

  return (
    <div className="flex min-h-screen bg-background">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-foreground"
      >
        {t("app.skipToContent")}
      </a>

      {/* Desktop Sidebar */}
      <aside className="hidden w-64 shrink-0 border-r border-border bg-card lg:flex lg:flex-col">
        <div className="flex h-14 items-center gap-2 border-b border-border px-5 text-primary">
          <Building2 className="h-5 w-5" aria-hidden="true" />
          <span className="font-bold tracking-tight">{t("app.name")}</span>
        </div>
        <nav aria-label="Main navigation" className="flex-1 space-y-1 p-3">
          {visibleNav.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-foreground hover:bg-secondary",
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                {t(item.labelKey)}
              </NavLink>
            );
          })}
        </nav>
        <div className="border-t border-border p-4 text-xs text-muted-foreground">
          <p className="truncate font-medium text-foreground">{user?.full_name ?? ""}</p>
          <p className="truncate">{user?.email ?? ""}</p>
        </div>
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen ? (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div className="fixed inset-0 bg-foreground/30" onClick={() => { setMobileOpen(false); }} />
          <aside className="relative z-50 flex w-64 flex-col bg-card shadow-xl">
            <div className="flex h-14 items-center justify-between border-b border-border px-4">
              <span className="font-bold text-primary">{t("app.name")}</span>
              <Button
                variant="ghost"
                size="sm"
                aria-label="Close menu"
                onClick={() => { setMobileOpen(false); }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <nav aria-label="Mobile navigation" className="flex-1 space-y-1 p-3">
              {visibleNav.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    onClick={() => { setMobileOpen(false); }}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "text-foreground hover:bg-secondary",
                      )
                    }
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {t(item.labelKey)}
                  </NavLink>
                );
              })}
            </nav>
          </aside>
        </div>
      ) : null}

      {/* Main Column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border bg-card px-4 sm:px-6">
          <Button
            variant="ghost"
            size="sm"
            className="lg:hidden"
            aria-label="Open menu"
            onClick={() => { setMobileOpen(true); }}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="ml-auto flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={toggleBanglaDigits}>
              {t("app.banglaDigits")}: {banglaDigits ? "চালু" : "Off"}
            </Button>
            <Button variant="outline" size="sm" onClick={toggleLanguage}>
              <Languages className="h-4 w-4" aria-hidden="true" />
              {i18n.language === "bn" ? "English" : "বাংলা"}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => void logout()}>
              <LogOut className="h-4 w-4" aria-hidden="true" />
              <span className="hidden sm:inline">{t("app.logout")}</span>
            </Button>
          </div>
        </header>

        <main id="main-content" className="mx-auto w-full max-w-6xl flex-1 p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
