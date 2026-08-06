"use client";

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import { api, setAuthToken } from "@/lib/api";
import { AuthResponse } from "@/lib/types";

type AuthContextValue = {
  username: string | null;
  loading: boolean; // true until we've read persisted state on mount
  login: (username: string, passphrase?: string) => Promise<AuthResponse>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const USERNAME_KEY = "ss_username";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore the session from localStorage on first mount, then confirm the
  // token is still valid with the backend (so a stale/rotated token logs out
  // cleanly instead of showing a signed-in shell that 401s on every call).
  useEffect(() => {
    const token = typeof window !== "undefined" ? window.localStorage.getItem("ss_token") : null;
    const savedName = typeof window !== "undefined" ? window.localStorage.getItem(USERNAME_KEY) : null;
    if (!token) {
      setLoading(false);
      return;
    }
    setAuthToken(token);
    setUsername(savedName);
    api
      .getMe()
      .then((me) => setUsername(me.username))
      .catch(() => {
        setAuthToken(null);
        if (typeof window !== "undefined") window.localStorage.removeItem(USERNAME_KEY);
        setUsername(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (name: string, passphrase?: string) => {
    const res = await api.login(name, passphrase);
    setAuthToken(res.token);
    if (typeof window !== "undefined") window.localStorage.setItem(USERNAME_KEY, res.username);
    setUsername(res.username);
    return res;
  }, []);

  const logout = useCallback(() => {
    setAuthToken(null);
    if (typeof window !== "undefined") window.localStorage.removeItem(USERNAME_KEY);
    setUsername(null);
  }, []);

  return <AuthContext.Provider value={{ username, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
