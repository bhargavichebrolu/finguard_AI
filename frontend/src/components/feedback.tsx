/**
 * The loading, empty, error and confirmation states every page uses (PRD 7.5).
 */
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

import type { ApiError } from "../services/api";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <Loader2 className="state-icon spin" aria-hidden="true" />
      <span>{label}…</span>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="state">
      <Inbox className="state-icon" aria-hidden="true" />
      <strong>{title}</strong>
      {children ? <p className="muted">{children}</p> : null}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  return (
    <div className="state state-error" role="alert">
      <AlertTriangle className="state-icon" aria-hidden="true" />
      <strong>{error.message}</strong>
      {error.fieldErrors.length > 0 ? (
        <ul className="field-errors">
          {error.fieldErrors.map((item) => (
            <li key={`${item.location}-${item.message}`}>
              {item.location ? `${item.location}: ` : ""}
              {item.message}
            </li>
          ))}
        </ul>
      ) : null}
      {error.requestId ? <p className="muted small">Reference: {error.requestId}</p> : null}
      {onRetry ? (
        <button type="button" className="button secondary" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="page-header">
      <h1>{title}</h1>
      {children ? <div className="page-intro">{children}</div> : null}
    </header>
  );
}

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Ask before a significant action. Escape and the cancel button both back out. */
export function ConfirmDialog({ open, title, message, confirmLabel, onConfirm, onCancel }: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    cancelRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;
  return (
    <div className="dialog-backdrop">
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <h2 id="confirm-title">{title}</h2>
        <div className="dialog-body">{message}</div>
        <div className="dialog-actions">
          <button ref={cancelRef} type="button" className="button secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="button primary" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
