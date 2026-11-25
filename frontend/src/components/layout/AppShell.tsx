import {
  Banknote,
  BarChart3,
  BookOpen,
  Building2,
  FileCheck2,
  FileSpreadsheet,
  IdCard,
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
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/features/auth/store";
import { cn } from "@/lib/cn";

interface NavItem {
  to: string;
  labelKey: string;
  icon: React.ComponentType<{ className?: string }>;
  permission?: string;
}

interface NavGroup {
  labelKey: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    labelKey: "navGroup.overview",
    items: [{ to: "/", labelKey: "nav.dashboard", icon: LayoutDashboard }],
  },
  {
    labelKey: "navGroup.accounting",
    items: [
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
    ],
  },
  {
    labelKey: "navGroup.commercial",
    items: [
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
    ],
  },
  {
    labelKey: "navGroup.inventory",
    items: [
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
    ],
  },
  {
    labelKey: "navGroup.compliance",
    items: [
      {
        to: "/vat/mushak",
        labelKey: "nav.vatMushak",
        icon: FileCheck2,
        permission: "vat.reports.read",
      },
    ],
  },
  {
    labelKey: "navGroup.people",
    items: [
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
    ],
  },
  {
    labelKey: "navGroup.system",
    items: [
      {
        to: "/audit-logs",
        labelKey: "nav.auditLogs",
        icon: ShieldAlert,
        permission: "audit.read",
      },
    ],
  },
];

const ALL_NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

const MOBILE_BOTTOM_ITEMS: NavItem[] = [
  { to: "/", labelKey: "nav.dashboard", icon: LayoutDashboard },
  {
    to: "/sales/invoices",
    labelKey: "nav.invoices",
    icon: Receipt,
    permission: "sales.invoices.read",
  },
  {
    to: "/inventory/stock",
    labelKey: "nav.stock",
    icon: Warehouse,
    permission: "inventory.stock.read",
  },
  {
    to: "/reports/statements",
    labelKey: "nav.financialStatements",
    icon: BarChart3,
    permission: "accounting.reports.read",
  },
];

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return "U";
  }
  const first = parts[0]?.charAt(0) ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1]?.charAt(0) ?? "") : "";
  return (first + last).toUpperCase();
}

interface SidebarNavProps {
  groups: NavGroup[];
  label: string;
  onNavigate?: () => void;
}

function SidebarNav({ groups, label, onNavigate }: SidebarNavProps): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <nav aria-label={label} className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
      {groups.map((group) => (
        <div key={group.labelKey}>
          <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            {t(group.labelKey)}
          </p>
          <ul className="space-y-0.5">
            {group.items.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.to === "/"}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      cn(
                        "group flex min-h-[38px] items-center gap-3 rounded-md px-3 py-2 text-[13px] font-medium transition-all duration-150",
                        isActive
                          ? "bg-sidebar-accent font-semibold text-primary shadow-[inset_3px_0_0_0_hsl(var(--primary))]"
                          : "text-sidebar-foreground hover:bg-muted hover:text-foreground",
                      )
                    }
                  >
                    <Icon className="h-4 w-4 shrink-0 opacity-85" aria-hidden="true" />
                    <span className="truncate">{t(item.labelKey)}</span>
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function BrandMark(): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-5">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
        <Building2 className="h-4 w-4" aria-hidden="true" />
      </span>
      <div className="leading-tight">
        <p className="text-sm font-semibold tracking-tight text-foreground">{t("app.name")}</p>
        <p className="text-[11px] text-muted-foreground">{t("app.vendor")}</p>
      </div>
    </div>
  );
}

export function AppShell(): React.JSX.Element {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const permissions = useAuthStore((s) => s.permissions);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);
  const toggleBanglaDigits = useAuthStore((s) => s.toggleBanglaDigits);
  const logout = useAuthStore((s) => s.logout);
  const [mobileOpen, setMobileOpen] = React.useState(false);

  // Smooth scroll to top when navigating between routes
  React.useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [location.pathname]);

  // Close mobile drawer on Escape key & lock body scroll while open
  React.useEffect(() => {
    if (!mobileOpen) return;
    const onKeyDown = (e: KeyboardEvent): void => {
      if (e.key === "Escape") {
        setMobileOpen(false);
      }
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [mobileOpen]);

  const visibleGroups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.permission || permissions.includes(item.permission)),
  })).filter((group) => group.items.length > 0);

  const visibleBottomItems = MOBILE_BOTTOM_ITEMS.filter(
    (item) => !item.permission || permissions.includes(item.permission),
  );

  const currentNavItem = ALL_NAV_ITEMS.find((item) => item.to === location.pathname);
  const currentTitle = currentNavItem ? t(currentNavItem.labelKey) : t("app.name");

  const isBangla = i18n.language === "bn";
  const setLanguage = (lang: "bn" | "en"): void => {
    void i18n.changeLanguage(lang);
  };

  const userName = user?.full_name ?? "";

  const userCard = (
    <div className="border-t border-sidebar-border p-3">
      <div className="flex items-center gap-3 rounded-md px-2 py-1.5">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
          {initialsOf(userName)}
        </span>
        <div className="min-w-0 flex-1 leading-tight">
          <p className="truncate text-[13px] font-medium text-foreground">{userName}</p>
          <p className="truncate text-[11px] text-muted-foreground">{user?.email ?? ""}</p>
        </div>
        <button
          type="button"
          aria-label={t("app.logout")}
          title={t("app.logout")}
          onClick={() => void logout()}
          className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <LogOut className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-background">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-foreground"
      >
        {t("app.skipToContent")}
      </a>

      {/* Desktop Sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
        <BrandMark />
        <SidebarNav groups={visibleGroups} label="Main navigation" />
        {userCard}
      </aside>

      {/* Mobile Slide-Over Drawer */}
      <div
        className={cn(
          "fixed inset-0 z-50 flex transition-opacity duration-200 lg:hidden",
          mobileOpen ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
        )}
        aria-hidden={!mobileOpen}
      >
        <div
          className="fixed inset-0 bg-foreground/40 backdrop-blur-[1px]"
          onClick={() => {
            setMobileOpen(false);
          }}
        />
        <aside
          className={cn(
            "relative z-10 flex h-full w-72 max-w-[85vw] flex-col border-r border-sidebar-border bg-sidebar shadow-2xl transition-transform duration-200 ease-out",
            mobileOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <div className="flex items-center justify-between pr-3">
            <BrandMark />
            <button
              type="button"
              aria-label="Close menu"
              onClick={() => {
                setMobileOpen(false);
              }}
              className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <SidebarNav
            groups={visibleGroups}
            label="Mobile navigation"
            onNavigate={() => {
              setMobileOpen(false);
            }}
          />
          {userCard}
        </aside>
      </div>

      {/* Main Column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-2 border-b border-border bg-card/90 px-3 backdrop-blur sm:h-16 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-9 w-9 p-0 lg:hidden"
              aria-label="Open menu"
              onClick={() => {
                setMobileOpen(true);
              }}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <span className="truncate text-sm font-semibold tracking-tight text-foreground">
              {currentTitle}
            </span>
          </div>

          <div className="ml-auto flex shrink-0 items-center gap-2 sm:gap-3">
            <button
              type="button"
              role="switch"
              aria-checked={banglaDigits}
              onClick={toggleBanglaDigits}
              className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span className="hidden sm:inline">{t("app.banglaDigits")}</span>
              <span className="sm:hidden">১২৩</span>
              <span
                className={cn(
                  "relative inline-flex h-5 w-9 items-center rounded-full transition-colors",
                  banglaDigits ? "bg-primary" : "bg-input",
                )}
              >
                <span
                  className={cn(
                    "inline-block h-4 w-4 rounded-full bg-white shadow transition-transform",
                    banglaDigits ? "translate-x-4" : "translate-x-0.5",
                  )}
                />
              </span>
            </button>

            <div
              role="group"
              aria-label={t("app.language")}
              className="inline-flex rounded-md border border-input bg-card p-0.5 shadow-sm"
            >
              <button
                type="button"
                aria-pressed={isBangla}
                onClick={() => {
                  setLanguage("bn");
                }}
                className={cn(
                  "rounded px-2 py-1 text-xs font-medium transition-colors sm:px-2.5",
                  isBangla
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted",
                )}
              >
                বাংলা
              </button>
              <button
                type="button"
                aria-pressed={!isBangla}
                onClick={() => {
                  setLanguage("en");
                }}
                className={cn(
                  "rounded px-2 py-1 text-xs font-medium transition-colors sm:px-2.5",
                  !isBangla
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted",
                )}
              >
                EN
              </button>
            </div>
          </div>
        </header>

        <main
          id="main-content"
          key={location.pathname}
          className="page-enter mx-auto w-full max-w-7xl flex-1 p-4 pb-24 sm:p-6 lg:p-8 lg:pb-8"
        >
          <Outlet />
        </main>
      </div>

      {/* Mobile Bottom Quick Navigation Bar */}
      <nav
        data-mobile-bottom-nav="true"
        aria-label="Mobile quick navigation"
        className="fixed inset-x-0 bottom-0 z-40 flex items-center justify-around border-t border-border bg-card/95 px-1 py-1.5 backdrop-blur lg:hidden"
      >
        {visibleBottomItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-md px-1 py-1.5 text-[10px] font-medium transition-colors",
                  isActive ? "text-primary" : "text-muted-foreground hover:text-foreground",
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="max-w-full truncate">{t(item.labelKey)}</span>
            </NavLink>
          );
        })}
        <button
          type="button"
          onClick={() => {
            setMobileOpen(true);
          }}
          className="flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-md px-1 py-1.5 text-[10px] font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <Menu className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span className="truncate">{t("nav.more")}</span>
        </button>
      </nav>
    </div>
  );
}
