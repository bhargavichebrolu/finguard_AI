/**
 * Settings (PRD 6.10): current settings, versions and dataset; for administrators the high risk
 * boundary and account management; for everyone a password change. The frozen threshold is shown
 * but cannot be changed, because the authorisation forbids it.
 */
import { useState, type FormEvent } from "react";

import { ConfirmDialog, ErrorState, LoadingState, PageHeader } from "../components/feedback";
import { DataTable, Pager, type Column } from "../components/DataTable";
import { useApiResource } from "../hooks/useApiResource";
import { useAuth } from "../hooks/useAuth";
import { api, ApiError, toApiError } from "../services/api";
import { settingsApi, usersApi, type AppSettings, type User, type UserCreate } from "../services/endpoints";
import { formatCount, formatDateTime, formatScore, humanise } from "../utils/format";

const ROLES = ["analyst", "investigator", "admin", "demo"] as const;
const MIN_PASSWORD = 12;
const USERS_PAGE_SIZE = 20;

/** Check a proposed high risk boundary against the frozen threshold. Returns a message or null. */
export function checkBoundary(text: string, frozenThreshold: number): string | null {
  const value = Number(text);
  if (text.trim() === "" || !Number.isFinite(value)) return "Enter a number.";
  if (value <= frozenThreshold || value > 1) {
    return `Enter a value above the frozen threshold (${formatScore(frozenThreshold)}) and at most 1.`;
  }
  return null;
}

export function SettingsPage() {
  const { can } = useAuth();
  const settings = useApiResource(() => settingsApi.get(), []);
  return (
    <section>
      <PageHeader title="Settings">Risk bands, versions, data source and accounts.</PageHeader>
      {settings.loading ? <LoadingState /> : null}
      {settings.error ? <ErrorState error={settings.error} onRetry={settings.reload} /> : null}
      {settings.data ? (
        <>
          <SettingsFacts settings={settings.data} />
          {can("update_settings") ? <BoundaryForm settings={settings.data} onSaved={settings.reload} /> : null}
        </>
      ) : null}
      <PasswordForm />
      {can("manage_users") ? <UserManagement /> : null}
    </section>
  );
}

function SettingsFacts({ settings }: { settings: AppSettings }) {
  return (
    <div className="grid two">
      <article className="card">
        <h2>Risk bands</h2>
        <dl className="facts">
          <dt>Review threshold</dt>
          <dd>
            {formatScore(settings.frozen_threshold)}{" "}
            <span className="muted">(frozen with the model; cannot be changed)</span>
          </dd>
          <dt>High risk boundary</dt>
          <dd>{formatScore(settings.high_risk_boundary)}</dd>
        </dl>
        <p className="muted small">{settings.risk_bands}</p>
      </article>
      <article className="card">
        <h2>Versions and limits</h2>
        <dl className="facts">
          <dt>Application</dt>
          <dd>{settings.application_version}</dd>
          <dt>Model</dt>
          <dd>{settings.model_version}</dd>
          <dt>Database</dt>
          <dd>{settings.database_available ? "Available" : "Unavailable"}</dd>
          <dt>Upload limit</dt>
          <dd>
            {formatCount(settings.max_upload_bytes)} bytes, {formatCount(settings.max_batch_rows)} rows
          </dd>
          <dt>Dataset</dt>
          <dd>{settings.dataset.name}</dd>
          <dt>Source file</dt>
          <dd className="wrap">{settings.dataset.source_file}</dd>
          <dt>Feature schema</dt>
          <dd>{settings.dataset.feature_schema_version}</dd>
        </dl>
      </article>
    </div>
  );
}

function BoundaryForm({ settings, onSaved }: { settings: AppSettings; onSaved: () => void }) {
  const [text, setText] = useState(String(settings.high_risk_boundary));
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [confirming, setConfirming] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const problem = checkBoundary(text, settings.frozen_threshold);
    setMessage(problem);
    if (!problem) setConfirming(true);
  }

  async function save() {
    setConfirming(false);
    setError(null);
    try {
      await settingsApi.update(Number(text));
      setMessage("Saved. New predictions use this boundary; stored predictions keep theirs.");
      onSaved();
    } catch (caught) {
      setError(toApiError(caught));
    }
  }

  return (
    <form className="card narrow" onSubmit={submit}>
      <h2>Change the high risk boundary</h2>
      <p className="muted small">
        This moves only the line between Medium and High for future predictions. It never changes
        which transactions are flagged, because the review threshold is frozen.
      </p>
      <label htmlFor="boundary">High risk boundary</label>
      <input id="boundary" inputMode="decimal" value={text} onChange={(event) => setText(event.target.value)} />
      {message ? <p className={message.startsWith("Saved") ? "notice" : "error-text"} role="status">{message}</p> : null}
      {error ? <ErrorState error={error} /> : null}
      <button type="submit" className="button primary form-submit">
        Save boundary
      </button>
      <ConfirmDialog
        open={confirming}
        title="Change the high risk boundary?"
        message={`Future predictions at or above ${text} will be labelled High. This is recorded in the audit log.`}
        confirmLabel="Change boundary"
        onCancel={() => setConfirming(false)}
        onConfirm={() => void save()}
      />
    </form>
  );
}

function PasswordForm() {
  const { signOut } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const tooShort = next.length > 0 && next.length < MIN_PASSWORD;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await api.post("/api/v1/auth/change-password", { current_password: current, new_password: next });
      await signOut();
    } catch (caught) {
      setError(toApiError(caught));
    }
  }

  return (
    <form className="card narrow" onSubmit={(event) => void submit(event)}>
      <h2>Change your password</h2>
      <p className="muted small">This signs you out everywhere, including this browser.</p>
      <label htmlFor="current-password">Current password</label>
      <input id="current-password" type="password" autoComplete="current-password" value={current} onChange={(event) => setCurrent(event.target.value)} />
      <label htmlFor="new-password">New password</label>
      <input
        id="new-password"
        type="password"
        autoComplete="new-password"
        value={next}
        onChange={(event) => setNext(event.target.value)}
        aria-describedby="new-password-hint"
      />
      <p id="new-password-hint" className={tooShort ? "error-text" : "hint"}>
        At least {MIN_PASSWORD} characters. A passphrase works well.
      </p>
      {error ? <ErrorState error={error} /> : null}
      <button type="submit" className="button primary form-submit" disabled={!current || next.length < MIN_PASSWORD}>
        Change password
      </button>
    </form>
  );
}

function UserManagement() {
  const { user: me } = useAuth();
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const users = useApiResource(() => usersApi.list(USERS_PAGE_SIZE, offset), [offset, refresh]);
  const [error, setError] = useState<ApiError | null>(null);
  const [pending, setPending] = useState<User | null>(null);

  async function change(target: User, update: Parameters<typeof usersApi.update>[1]) {
    setError(null);
    try {
      await usersApi.update(target.id, update);
      setRefresh((count) => count + 1);
    } catch (caught) {
      setError(toApiError(caught));
    }
  }

  const columns: Column<User>[] = [
    { key: "email", header: "Email", render: (row) => row.email },
    {
      key: "role",
      header: "Role",
      render: (row) => (
        <select
          aria-label={`Role for ${row.email}`}
          value={row.role}
          onChange={(event) => void change(row, { role: event.target.value as User["role"] })}
        >
          {ROLES.map((role) => (
            <option key={role} value={role}>
              {humanise(role)}
            </option>
          ))}
        </select>
      ),
    },
    { key: "active", header: "Active", render: (row) => (row.is_active ? "Yes" : "No") },
    { key: "created", header: "Created", render: (row) => formatDateTime(row.created_at) },
    {
      key: "action",
      header: "Access",
      render: (row) =>
        row.is_active ? (
          <button type="button" className="button secondary" onClick={() => setPending(row)} disabled={row.id === me?.id}>
            Deactivate
          </button>
        ) : (
          <button type="button" className="button secondary" onClick={() => void change(row, { is_active: true })}>
            Reactivate
          </button>
        ),
    },
  ];

  return (
    <article className="card">
      <h2>Accounts</h2>
      {error ? <ErrorState error={error} /> : null}
      {users.loading ? <LoadingState /> : null}
      {users.data ? (
        <>
          <DataTable caption="Accounts" columns={columns} rows={users.data.items} rowKey={(row) => row.id} emptyTitle="No accounts" />
          <Pager total={users.data.total} limit={USERS_PAGE_SIZE} offset={offset} onChange={setOffset} />
        </>
      ) : null}
      <CreateUserForm onCreated={() => setRefresh((count) => count + 1)} />
      <ConfirmDialog
        open={pending !== null}
        title={`Deactivate ${pending?.email ?? ""}?`}
        message="They are signed out at once and cannot sign in until reactivated. Their records are kept."
        confirmLabel="Deactivate"
        onCancel={() => setPending(null)}
        onConfirm={() => {
          if (pending) void change(pending, { is_active: false });
          setPending(null);
        }}
      />
    </article>
  );
}

function CreateUserForm({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState<UserCreate>({ email: "", password: "", role: "analyst" });
  const [error, setError] = useState<ApiError | null>(null);
  const [created, setCreated] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setCreated(null);
    try {
      const user = await usersApi.create(form);
      setCreated(user.email);
      setForm({ email: "", password: "", role: "analyst" });
      onCreated();
    } catch (caught) {
      setError(toApiError(caught));
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)}>
      <h3>Create an account</h3>
      <div className="filter-grid">
        <div>
          <label htmlFor="new-email">Email</label>
          <input id="new-email" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
        </div>
        <div>
          <label htmlFor="new-user-password">Temporary password</label>
          <input id="new-user-password" type="password" autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
        </div>
        <div>
          <label htmlFor="new-role">Role</label>
          <select id="new-role" value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value as UserCreate["role"] })}>
            {ROLES.map((role) => (
              <option key={role} value={role}>
                {humanise(role)}
              </option>
            ))}
          </select>
        </div>
      </div>
      {created ? <p className="notice" role="status">Created {created}. Share the temporary password privately.</p> : null}
      {error ? <ErrorState error={error} /> : null}
      <button type="submit" className="button primary form-submit" disabled={!form.email || form.password.length < MIN_PASSWORD}>
        Create account
      </button>
    </form>
  );
}
