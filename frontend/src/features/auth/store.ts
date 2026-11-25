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

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  permissions: string[];
  banglaDigits: boolean;
  setSession: (tokens: TokenResponse, user: AuthUser, permissions: string[]) => void;
  toggleBanglaDigits: () => void;
  clearSession: () => void;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  permissions: [],
  banglaDigits: false,

  setSession: (tokens, user, permissions) => {
    set({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      user,
      permissions,
    });
  },

  toggleBanglaDigits: () => {
    set((state) => ({ banglaDigits: !state.banglaDigits }));
  },

  clearSession: () => {
    set({ accessToken: null, refreshToken: null, user: null, permissions: [] });
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
