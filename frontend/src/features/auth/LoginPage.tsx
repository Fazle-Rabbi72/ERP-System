import { zodResolver } from "@hookform/resolvers/zod";
import { Building2, Languages, Lock, ShieldCheck } from "lucide-react";
import * as React from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-10">
      <div className="mb-6 flex w-full max-w-md items-center justify-between">
        <div className="flex items-center gap-2 text-primary">
          <Building2 className="h-6 w-6" aria-hidden="true" />
          <span className="text-lg font-bold tracking-tight">{t("app.name")}</span>
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

      <main id="main-content" className="w-full max-w-md">
        <Card>
          <CardHeader>
            <CardTitle>{t("auth.title")}</CardTitle>
            <p className="text-sm text-muted-foreground">{t("auth.subtitle")}</p>
          </CardHeader>
          <CardContent>
            {serverError ? (
              <div
                role="alert"
                className="mb-4 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
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
                <Label htmlFor="otp_code" className="flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                  {t("auth.otpCode")}
                </Label>
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
                <Lock className="h-4 w-4" aria-hidden="true" />
                {isSubmitting ? t("auth.signingIn") : t("auth.signIn")}
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="mt-6 text-center text-xs text-muted-foreground">{t("app.vendor")}</p>
      </main>
    </div>
  );
}
