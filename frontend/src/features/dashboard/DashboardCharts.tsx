import { BarChart3, PieChart as PieChartIcon } from "lucide-react";
import * as React from "react";
import { useTranslation } from "react-i18next";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardSummary } from "@/features/reports/types";
import { formatBDT } from "@/lib/format";

interface DashboardChartsProps {
  summary: DashboardSummary;
  banglaDigits: boolean;
}

const CHART_PALETTE = [
  "#1e40af", // Corporate Navy
  "#3b82f6", // Steel Blue
  "#0f766e", // Deep Teal
  "#475569", // Slate
  "#6366f1", // Indigo
  "#94a3b8", // Muted Slate
];

function compactAxis(value: number): string {
  if (Math.abs(value) >= 10_000_000) {
    return `${(value / 10_000_000).toFixed(1)}Cr`;
  }
  if (Math.abs(value) >= 100_000) {
    return `${(value / 100_000).toFixed(1)}L`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${(value / 1_000).toFixed(0)}K`;
  }
  return String(value);
}

export function DashboardCharts({
  summary,
  banglaDigits,
}: DashboardChartsProps): React.JSX.Element {
  const { t } = useTranslation();
  const [trendMode, setTrendMode] = React.useState<"area" | "bar">("area");

  const trendData = summary.monthly_trend.map((pt) => ({
    month: pt.month,
    revenue: Number(pt.revenue),
    expense: Number(pt.expense),
    netProfit: Number(pt.net_profit),
  }));

  const positionData = [
    { name: t("reports.totalAssets"), value: Math.max(0, Number(summary.total_assets)) },
    { name: t("reports.totalLiabilities"), value: Math.max(0, Number(summary.total_liabilities)) },
    { name: t("dashboard.arDue"), value: Math.max(0, Number(summary.accounts_receivable_due)) },
    { name: t("dashboard.apDue"), value: Math.max(0, Number(summary.accounts_payable_due)) },
  ].filter((d) => d.value > 0);

  const expenseData = summary.expense_breakdown
    .map((line) => ({
      name: line.name,
      value: Math.max(0, Number(line.amount)),
    }))
    .filter((d) => d.value > 0)
    .slice(0, 6);

  const pieData = (expenseData.length > 0 ? expenseData : positionData).map((entry, idx) => ({
    ...entry,
    fill: CHART_PALETTE[idx % CHART_PALETTE.length],
  }));
  const pieTitle =
    expenseData.length > 0 ? t("dashboard.expenseBreakdown") : t("dashboard.financialPosition");

  const formatTooltipValue = (
    value: number | string | ReadonlyArray<number | string> | undefined,
  ): string => {
    const first: number | string | undefined = Array.isArray(value)
      ? (value as ReadonlyArray<number | string>)[0]
      : (value as number | string | undefined);
    return formatBDT(Number(first ?? 0).toFixed(2), { banglaDigits });
  };

  return (
    <section
      aria-label={t("dashboard.analyticsTitle")}
      className="grid gap-4 lg:grid-cols-12"
    >
      {/* Monthly Revenue vs Expense Trend Chart */}
      <Card className="lg:col-span-7">
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pb-3">
          <div>
            <CardTitle>{t("dashboard.trendTitle")}</CardTitle>
            <p className="mt-0.5 text-xs text-muted-foreground">{t("dashboard.trendSubtitle")}</p>
          </div>
          <div className="inline-flex rounded-md border border-input bg-background p-0.5">
            <Button
              variant={trendMode === "area" ? "default" : "ghost"}
              size="sm"
              className="h-7 px-2.5 text-xs"
              onClick={() => {
                setTrendMode("area");
              }}
            >
              {t("dashboard.chartArea")}
            </Button>
            <Button
              variant={trendMode === "bar" ? "default" : "ghost"}
              size="sm"
              className="h-7 px-2.5 text-xs"
              onClick={() => {
                setTrendMode("bar");
              }}
            >
              {t("dashboard.chartBar")}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {trendData.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/20 px-4 text-center">
              <BarChart3 className="mb-2 h-6 w-6 text-muted-foreground" aria-hidden="true" />
              <p className="text-sm font-medium text-foreground">{t("dashboard.noChartData")}</p>
              <p className="mt-1 max-w-xs text-xs text-muted-foreground">
                {t("dashboard.noChartDataDesc")}
              </p>
            </div>
          ) : (
            <div className="h-64 w-full sm:h-72">
              <ResponsiveContainer width="100%" height="100%">
                {trendMode === "area" ? (
                  <AreaChart data={trendData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#1e40af" stopOpacity={0.28} />
                        <stop offset="95%" stopColor="#1e40af" stopOpacity={0.02} />
                      </linearGradient>
                      <linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#64748b" stopOpacity={0.24} />
                        <stop offset="95%" stopColor="#64748b" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis
                      dataKey="month"
                      tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tickFormatter={compactAxis}
                      tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                      width={52}
                    />
                    <Tooltip
                      formatter={formatTooltipValue}
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        borderColor: "hsl(var(--border))",
                        borderRadius: "0.5rem",
                        fontSize: "12px",
                        boxShadow: "0 4px 12px rgba(15,23,42,0.08)",
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px" }} />
                    <Area
                      type="monotone"
                      dataKey="revenue"
                      name={t("reports.totalRevenue")}
                      stroke="#1e40af"
                      strokeWidth={2}
                      fill="url(#revGrad)"
                    />
                    <Area
                      type="monotone"
                      dataKey="expense"
                      name={t("reports.totalExpense")}
                      stroke="#64748b"
                      strokeWidth={2}
                      fill="url(#expGrad)"
                    />
                  </AreaChart>
                ) : (
                  <BarChart data={trendData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis
                      dataKey="month"
                      tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tickFormatter={compactAxis}
                      tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                      width={52}
                    />
                    <Tooltip
                      formatter={formatTooltipValue}
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        borderColor: "hsl(var(--border))",
                        borderRadius: "0.5rem",
                        fontSize: "12px",
                        boxShadow: "0 4px 12px rgba(15,23,42,0.08)",
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px" }} />
                    <Bar
                      dataKey="revenue"
                      name={t("reports.totalRevenue")}
                      fill="#1e40af"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="expense"
                      name={t("reports.totalExpense")}
                      fill="#64748b"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Donut Chart: Expense Breakdown or Financial Position */}
      <Card className="lg:col-span-5">
        <CardHeader className="pb-3">
          <CardTitle>{pieTitle}</CardTitle>
          <p className="mt-0.5 text-xs text-muted-foreground">{t("dashboard.distributionSubtitle")}</p>
        </CardHeader>
        <CardContent>
          {pieData.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/20 px-4 text-center">
              <PieChartIcon className="mb-2 h-6 w-6 text-muted-foreground" aria-hidden="true" />
              <p className="text-sm font-medium text-foreground">{t("dashboard.noChartData")}</p>
              <p className="mt-1 max-w-xs text-xs text-muted-foreground">
                {t("dashboard.noChartDataDesc")}
              </p>
            </div>
          ) : (
            <div className="h-64 w-full sm:h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="46%"
                    innerRadius={54}
                    outerRadius={84}
                    paddingAngle={2}
                  />
                  <Tooltip
                    formatter={formatTooltipValue}
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      borderColor: "hsl(var(--border))",
                      borderRadius: "0.5rem",
                      fontSize: "12px",
                      boxShadow: "0 4px 12px rgba(15,23,42,0.08)",
                    }}
                  />
                  <Legend height={36} wrapperStyle={{ fontSize: "12px" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
