import { create } from "zustand";

import { apiRequest } from "@/lib/api";

export interface AuthUser {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  mfa_enabled: boolean;
  last_login_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface EffectivePermissionsResponse {
  user_id: string;
  tenant_id: string;
  permissions: string[];
}

const REFRESH_STORAGE_KEY = "nexzen_refresh_token";
const BANGLA_DIGITS_KEY = "nexzen_bangla_digits";

function readRefreshToken(): string | null {
  try {
    return window.sessionStorage.getItem(REFRESH_STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeRefreshToken(token: string | null): void {
  try {
    if (token) {
      window.sessionStorage.setItem(REFRESH_STORAGE_KEY, token);
    } else {
      window.sessionStorage.removeItem(REFRESH_STORAGE_KEY);
    }
  } catch {
    // Ignore storage errors in restricted environments.
  }
}

function readBanglaDigits(): boolean {
  try {
    return window.localStorage.getItem(BANGLA_DIGITS_KEY) === "1";
  } catch {
    return false;
  }
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  permissions: string[];
  banglaDigits: boolean;
  isRestoring: boolean;
  setSession: (tokens: TokenResponse, user: AuthUser, permissions: string[]) => void;
  restoreSession: () => Promise<void>;
  toggleBanglaDigits: () => void;
  clearSession: () => void;
  logout: () => Promise<void>;
}

let restorePromise: Promise<void> | null = null;

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  refreshToken: readRefreshToken(),
  user: null,
  permissions: [],
  banglaDigits: readBanglaDigits(),
  isRestoring: Boolean(readRefreshToken()),

  setSession: (tokens, user, permissions) => {
    writeRefreshToken(tokens.refresh_token);
    set({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      user,
      permissions,
      isRestoring: false,
    });
  },

  restoreSession: async () => {
    const existing = readRefreshToken();
    if (!existing || get().accessToken) {
      set({ isRestoring: false });
      return;
    }
    if (restorePromise) {
      await restorePromise;
      return;
    }

    set({ isRestoring: true });
    restorePromise = (async () => {
      try {
        const tokens = await apiRequest<TokenResponse>("/auth/refresh", {
          method: "POST",
          body: { refresh_token: existing },
        });
        const [user, permRes] = await Promise.all([
          apiRequest<AuthUser>("/auth/me", { accessToken: tokens.access_token }),
          apiRequest<EffectivePermissionsResponse>("/rbac/me/permissions", {
            accessToken: tokens.access_token,
          }),
        ]);
        writeRefreshToken(tokens.refresh_token);
        set({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          user,
          permissions: permRes.permissions,
          isRestoring: false,
        });
      } catch {
        writeRefreshToken(null);
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          permissions: [],
          isRestoring: false,
        });
      } finally {
        restorePromise = null;
      }
    })();

    await restorePromise;
  },

  toggleBanglaDigits: () => {
    set((state) => {
      const next = !state.banglaDigits;
      try {
        window.localStorage.setItem(BANGLA_DIGITS_KEY, next ? "1" : "0");
      } catch {
        // Ignore storage errors.
      }
      return { banglaDigits: next };
    });
  },

  clearSession: () => {
    writeRefreshToken(null);
    set({
      accessToken: null,
      refreshToken: null,
      user: null,
      permissions: [],
      isRestoring: false,
    });
  },

  logout: async () => {
    const { accessToken, refreshToken, clearSession } = get();
    try {
      if (accessToken) {
        await apiRequest<undefined>("/auth/logout", {
          method: "POST",
          accessToken,
          body: refreshToken ? { refresh_token: refreshToken } : undefined,
        });
      }
    } catch {
      // Always clear local session even if the server is unreachable.
    } finally {
      clearSession();
    }
  },
}));
