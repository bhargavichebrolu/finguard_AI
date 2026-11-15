/**
 * Who is signed in, and what they may do.
 *
 * The session lives in an HttpOnly cookie, so on start-up the only way to know whether one exists
 * is to ask the API. Permissions come from the API and are never derived here.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { ApiError, onUnauthorized, toApiError } from "../services/api";
import { authApi, type CurrentUser } from "../services/endpoints";

/** "unavailable": the session could not be checked because the server did not answer properly. */
export type AuthStatus = "checking" | "signedOut" | "signedIn" | "unavailable";

export interface AuthState {
  status: AuthStatus;
  user: CurrentUser | null;
  notice: string | null;
  /** Why the session could not be checked, while status is "unavailable". */
  checkError: ApiError | null;
  /** Check the session again, as after the server comes back. */
  recheck: () => void;
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
  const [checkError, setCheckError] = useState<ApiError | null>(null);
  const [attempt, setAttempt] = useState(0);

  const endSession = useCallback((message: string | null) => {
    setUser(null);
    setStatus("signedOut");
    setNotice(message);
  }, []);

  useEffect(() => {
    let active = true;
    setStatus("checking");
    authApi
      .me()
      .then((current) => {
        if (!active) return;
        setUser(current);
        setCheckError(null);
        setStatus("signedIn");
      })
      .catch((caught: unknown) => {
        if (!active) return;
        const error = toApiError(caught);
        // Only a 401 means there is no session. Anything else (no answer, a 5xx while the API or
        // database is down) says nothing about the session, which may be perfectly valid, so
        // the user is told the server is unavailable instead of being sent to sign in (Phase 5 M7).
        if (error.status === 401) {
          endSession(null);
        } else {
          setCheckError(error);
          setStatus("unavailable");
        }
      });
    return () => {
      active = false;
    };
  }, [endSession, attempt]);

  const recheck = useCallback(() => setAttempt((count) => count + 1), []);

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
    () => ({ status, user, notice, checkError, recheck, signIn, signOut, can }),
    [status, user, notice, checkError, recheck, signIn, signOut, can],
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
