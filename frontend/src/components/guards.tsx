/**
 * Route guards. They decide what to show; the API still refuses anything a role may not do.
 */
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { LoadingState } from "./feedback";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "checking") return <LoadingState label="Checking your session" />;
  if (status === "signedOut") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

export function RequirePermission({ permission, children }: { permission: string; children: ReactNode }) {
  const { can } = useAuth();
  if (!can(permission)) return <ForbiddenPage />;
  return <>{children}</>;
}

export function ForbiddenPage() {
  return (
    <section className="card narrow">
      <h1>Not available for your role</h1>
      <p className="muted">Ask an administrator if you need access to this page.</p>
    </section>
  );
}

export function NotFoundPage() {
  return (
    <section className="card narrow">
      <h1>Page not found</h1>
      <p className="muted">Use the navigation to choose a page.</p>
    </section>
  );
}
