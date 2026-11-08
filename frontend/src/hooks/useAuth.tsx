/**
 * Who is signed in, and what they may do.
 *
 * The session lives in an HttpOnly cookie, so on start-up the only way to know whether one exists
 * is to ask the API. Permissions come from the API and are never derived here.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { onUnauthorized } from "../services/api";
import { authApi, type CurrentUser } from "../services/endpoints";

export type AuthStatus = "checking" | "signedOut" | "signedIn";

export interface AuthState {
  status: AuthStatus;
  user: CurrentUser | null;
  notice: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  can: (permission: string) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);
const SESSION_ENDED = "Your session has ended. Please sign in again.";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const endSession = useCallback((message: string | null) => {
    setUser(null);
    setStatus("signedOut");
    setNotice(message);
  }, []);

  useEffect(() => {
    let active = true;
    authApi
      .me()
      .then((current) => {
        if (!active) return;
        setUser(current);
        setStatus("signedIn");
      })
      .catch(() => {
        if (active) endSession(null);
      });
    return () => {
      active = false;
    };
  }, [endSession]);

  useEffect(() => {
    onUnauthorized(() => endSession(SESSION_ENDED));
    return () => onUnauthorized(null);
  }, [endSession]);

  useEffect(() => {
    if (!user?.session_expires_at) return undefined;
    const remaining = new Date(user.session_expires_at).getTime() - Date.now();
    const timer = window.setTimeout(() => endSession(SESSION_ENDED), Math.max(remaining, 0));
    return () => window.clearTimeout(timer);
  }, [user, endSession]);

  const signIn = useCallback(async (email: string, password: string) => {
    const current = await authApi.signIn(email, password);
    setUser(current);
    setNotice(null);
    setStatus("signedIn");
  }, []);

  const signOut = useCallback(async () => {
    try {
      await authApi.signOut();
    } finally {
      endSession("You have signed out.");
    }
  }, [endSession]);

  const can = useCallback(
    (permission: string) => Boolean(user?.permissions.includes(permission)),
    [user],
  );

  const value = useMemo(
    () => ({ status, user, notice, signIn, signOut, can }),
    [status, user, notice, signIn, signOut, can],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const state = useContext(AuthContext);
  if (!state) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return state;
}
