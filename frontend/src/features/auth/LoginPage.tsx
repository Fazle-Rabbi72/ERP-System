import { zodResolver } from "@hookform/resolvers/zod";
import { Building2, FileCheck2, Languages, Scale, ShieldCheck } from "lucide-react";
import * as React from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  type AuthUser,
  type EffectivePermissionsResponse,
  type TokenResponse,
  useAuthStore,
} from "@/features/auth/store";
import { ApiError, apiRequest } from "@/lib/api";

const loginSchema = z.object({
  tenant_code: z.string().trim().max(64).optional(),
  email: z.string().trim().email(),
  password: z.string().min(1),
  otp_code: z
    .string()
    .trim()
    .refine((val) => val === "" || /^\d{6}$/.test(val), { message: "otp" })
    .optional(),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginPage(): React.JSX.Element {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const setSession = useAuthStore((s) => s.setSession);
  const [serverError, setServerError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      tenant_code: "",
      email: "",
      password: "",
      otp_code: "",
    },
  });

  const toggleLanguage = (): void => {
    void i18n.changeLanguage(i18n.language === "bn" ? "en" : "bn");
  };

  const onSubmit = async (values: LoginFormValues): Promise<void> => {
    setServerError(null);
    try {
      const payload: Record<string, string> = {
        email: values.email,
        password: values.password,
      };
      if (values.tenant_code) {
        payload.tenant_code = values.tenant_code;
      }
      if (values.otp_code) {
        payload.otp_code = values.otp_code;
      }

      const tokens = await apiRequest<TokenResponse>("/auth/login", {
        method: "POST",
        body: payload,
      });
      const [user, permRes] = await Promise.all([
        apiRequest<AuthUser>("/auth/me", { accessToken: tokens.access_token }),
        apiRequest<EffectivePermissionsResponse>("/rbac/me/permissions", {
          accessToken: tokens.access_token,
        }),
      ]);
      setSession(tokens, user, permRes.permissions);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setServerError(err.message);
      } else {
        setServerError("An unexpected error occurred.");
      }
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
      {/* Brand panel */}
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-sidebar p-12 text-white lg:flex">
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-primary/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-primary/20 blur-3xl" />

        <div className="relative flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/20">
            <Building2 className="h-5 w-5" aria-hidden="true" />
          </span>
          <div className="leading-tight">
            <p className="text-lg font-semibold tracking-tight">{t("app.name")}</p>
            <p className="text-xs text-white/60">{t("app.vendor")}</p>
          </div>
        </div>

        <div className="relative max-w-md space-y-8">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight">
            {t("auth.brandHeadline")}
          </h2>
          <ul className="space-y-5">
            {[
              { icon: Scale, text: t("auth.feature1") },
              { icon: FileCheck2, text: t("auth.feature2") },
              { icon: ShieldCheck, text: t("auth.feature3") },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.text} className="flex items-start gap-3 text-sm text-white/80">
                  <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10 ring-1 ring-white/15">
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <span className="pt-1 leading-snug">{item.text}</span>
                </li>
              );
            })}
          </ul>
        </div>

        <p className="relative text-xs text-white/50">{t("app.vendor")}</p>
      </aside>

      {/* Form panel */}
      <div className="flex flex-col bg-background px-4 py-8 sm:px-10">
        <div className="flex w-full items-center justify-between">
          <div className="flex items-center gap-2 text-primary lg:invisible">
            <Building2 className="h-5 w-5" aria-hidden="true" />
            <span className="text-base font-semibold tracking-tight">{t("app.name")}</span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={toggleLanguage}
            aria-label={t("app.language")}
          >
            <Languages className="h-4 w-4" aria-hidden="true" />
            {i18n.language === "bn" ? "English" : "বাংলা"}
          </Button>
        </div>

        <main id="main-content" className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-md">
            <div className="mb-6">
              <h1 className="text-2xl font-semibold tracking-tight">{t("auth.title")}</h1>
              <p className="mt-1.5 text-sm text-muted-foreground">{t("auth.subtitle")}</p>
            </div>

            <Card>
              <CardContent className="p-6">
                {serverError ? (
                  <div
                    role="alert"
                    className="mb-4 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
                  >
                    {serverError}
                  </div>
                ) : null}

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
                  <div className="space-y-1.5">
                    <Label htmlFor="tenant_code">{t("auth.tenantCode")}</Label>
                    <Input
                      id="tenant_code"
                      autoComplete="organization"
                      placeholder={t("auth.tenantCodePlaceholder")}
                      {...register("tenant_code")}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="email">{t("auth.email")}</Label>
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      aria-invalid={Boolean(errors.email)}
                      placeholder={t("auth.emailPlaceholder")}
                      {...register("email")}
                    />
                    {errors.email ? (
                      <p role="alert" className="text-xs text-destructive">
                        {t("auth.validation.email")}
                      </p>
                    ) : null}
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="password">{t("auth.password")}</Label>
                    <Input
                      id="password"
                      type="password"
                      autoComplete="current-password"
                      aria-invalid={Boolean(errors.password)}
                      {...register("password")}
                    />
                    {errors.password ? (
                      <p role="alert" className="text-xs text-destructive">
                        {t("auth.validation.password")}
                      </p>
                    ) : null}
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="otp_code">{t("auth.otpCode")}</Label>
                    <Input
                      id="otp_code"
                      inputMode="numeric"
                      maxLength={6}
                      autoComplete="one-time-code"
                      aria-invalid={Boolean(errors.otp_code)}
                      placeholder={t("auth.otpPlaceholder")}
                      {...register("otp_code")}
                    />
                    {errors.otp_code ? (
                      <p role="alert" className="text-xs text-destructive">
                        {t("auth.validation.otp")}
                      </p>
                    ) : null}
                  </div>

                  <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? t("auth.signingIn") : t("auth.signIn")}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </main>

        <p className="text-center text-xs text-muted-foreground">{t("app.vendor")}</p>
      </div>
    </div>
  );
}

