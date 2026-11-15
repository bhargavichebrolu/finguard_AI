/**
 * Investigation Centre (PRD 6.7): the review queue, each case's history and notes, and for
 * investigators and administrators the status, assignment and note actions. Statuses are workflow
 * labels, not verified criminal findings, and they never change a score or a decision.
 */
import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";

import { DecisionBadge, RiskBadge, StatusBadge } from "../components/badges";
import { DataTable, Pager, type Column } from "../components/DataTable";
import { ConfirmDialog, ErrorState, LoadingState, PageHeader } from "../components/feedback";
import { useApiResource } from "../hooks/useApiResource";
import { useAuth } from "../hooks/useAuth";
import { ApiError, toApiError } from "../services/api";
import {
  investigationsApi,
  usersApi,
  type InvestigationDetail,
  type InvestigationQuery,
  type InvestigationSummary,
  type InvestigationUpdate,
} from "../services/endpoints";
import { formatAmount, formatDateTime, formatScore, humanise } from "../utils/format";

const PAGE_SIZE = 25;
export const STATUSES = ["NEW", "UNDER_REVIEW", "ESCALATED", "CLOSED", "FALSE_ALARM"] as const;
/** Statuses that end a review. Choosing one asks for confirmation (PRD 7.5). */
export const CONCLUDING = new Set(["CLOSED", "FALSE_ALARM"]);
const WORKFLOW_NOTE =
  "Statuses are workflow labels. They are not verified criminal findings, and they never change a model score, a decision or a metric.";

const COLUMNS: Column<InvestigationSummary>[] = [
  { key: "txn", header: "Transaction", render: (row) => row.external_transaction_id },
  { key: "type", header: "Type", render: (row) => humanise(row.transaction_type) },
  { key: "amount", header: "Amount", render: (row) => formatAmount(row.amount), numeric: true },
  { key: "score", header: "Model score", render: (row) => formatScore(row.model_score), numeric: true },
  { key: "risk", header: "Risk", render: (row) => <RiskBadge level={row.risk_level} /> },
  { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
  { key: "assigned", header: "Assigned", render: (row) => (row.assigned_user_id ? "Yes" : "No") },
  { key: "updated", header: "Updated", render: (row) => formatDateTime(row.updated_at) },
];

export function InvestigationCentrePage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const [status, setStatus] = useState("");
  const [mineOnly, setMineOnly] = useState(false);
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const openId = params.get("open");

  const query: InvestigationQuery = { limit: PAGE_SIZE, offset };
  if (status) query.investigation_status = status as InvestigationQuery["investigation_status"];
  if (mineOnly && user) query.assigned_user_id = user.id;
  const queue = useApiResource(() => investigationsApi.list(query), [status, mineOnly, offset, refresh]);
  const selectedRow = queue.data?.items.find((row) => row.id === openId) ?? null;

  function open(id: string | null) {
    setParams(id ? { open: id } : {});
  }

  return (
    <section>
      <PageHeader title="Investigation Centre">
        Flagged transactions waiting for a person to review them. {WORKFLOW_NOTE}
      </PageHeader>
      <div className="card filters">
        <div className="filter-grid">
          <div>
            <label htmlFor="i-status">Status</label>
            <select id="i-status" value={status} onChange={(event) => { setStatus(event.target.value); setOffset(0); }}>
              <option value="">Any</option>
              {STATUSES.map((value) => (
                <option key={value} value={value}>
                  {humanise(value)}
                </option>
              ))}
            </select>
          </div>
          <div className="checkbox-field">
            <input
              id="i-mine"
              type="checkbox"
              checked={mineOnly}
              onChange={(event) => { setMineOnly(event.target.checked); setOffset(0); }}
            />
            <label htmlFor="i-mine">Assigned to me</label>
          </div>
        </div>
      </div>
      <article className="card">
        {queue.loading ? <LoadingState /> : null}
        {queue.error ? <ErrorState error={queue.error} onRetry={queue.reload} /> : null}
        {queue.data ? (
          <>
            <DataTable
              caption="Investigation queue"
              columns={COLUMNS}
              rows={queue.data.items}
              rowKey={(row) => row.id}
              emptyTitle="No investigations match"
              emptyMessage="Investigations open when the model flags a transaction for review."
              onRowSelect={(row) => open(row.id)}
              selectedKey={openId}
            />
            <Pager total={queue.data.total} limit={PAGE_SIZE} offset={offset} onChange={setOffset} />
          </>
        ) : null}
      </article>
      {openId ? (
        <InvestigationPanel
          key={openId}
          id={openId}
          summary={selectedRow}
          onClose={() => open(null)}
          onChanged={() => setRefresh((count) => count + 1)}
        />
      ) : null}
    </section>
  );
}

interface PanelProps {
  id: string;
  summary: InvestigationSummary | null;
  onClose: () => void;
  onChanged: () => void;
}

function InvestigationPanel({ id, summary, onClose, onChanged }: PanelProps) {
  const { can } = useAuth();
  const canUpdate = can("update_investigations");
  const detail = useApiResource(() => investigationsApi.get(id), [id]);
  const [actionError, setActionError] = useState<ApiError | null>(null);

  async function act(change: () => Promise<unknown>) {
    setActionError(null);
    try {
      await change();
      detail.reload();
      onChanged();
    } catch (caught) {
      const error = toApiError(caught);
      setActionError(error);
      if (error.status === 409) {
        // Someone else changed the case first: show what it is now beside the explanation.
        detail.reload();
        onChanged();
      }
    }
  }

  if (detail.loading && !detail.data) return <LoadingState label="Loading the investigation" />;
  if (detail.error) return <ErrorState error={detail.error} onRetry={detail.reload} />;
  if (!detail.data) return null;
  const investigation = detail.data;

  return (
    <section className="detail-panel" aria-label="Investigation">
      <div className="detail-header">
        <h2>Investigation{summary ? ` of ${summary.external_transaction_id}` : ""}</h2>
        <button type="button" className="button secondary" onClick={onClose}>
          Close
        </button>
      </div>
      <div className="grid two">
        <article className="card">
          <h2>Case</h2>
          <dl className="facts">
            <dt>Status</dt>
            <dd>
              <StatusBadge status={investigation.status} />
            </dd>
            {summary ? (
              <>
                <dt>Model decision</dt>
                <dd>
                  <DecisionBadge decision={summary.prediction} /> <RiskBadge level={summary.risk_level} />
                </dd>
                <dt>Model score (uncalibrated)</dt>
                <dd>{formatScore(summary.model_score)}</dd>
                <dt>Transaction</dt>
                <dd>
                  {humanise(summary.transaction_type)}, {formatAmount(summary.amount)}, step {summary.step}
                </dd>
              </>
            ) : null}
            <dt>Opened</dt>
            <dd>{formatDateTime(investigation.created_at)}</dd>
            <dt>Last updated</dt>
            <dd>{formatDateTime(investigation.updated_at)}</dd>
          </dl>
          <p className="muted small">{WORKFLOW_NOTE}</p>
          {actionError ? <ErrorState error={actionError} /> : null}
          {canUpdate ? (
            <>
              <StatusControl current={investigation.status} onChange={(next) => act(() => investigationsApi.update(id, { status: next, expected_status: investigation.status }))} />
              <AssigneeControl investigation={investigation} onChange={(change) => act(() => investigationsApi.update(id, change))} />
            </>
          ) : (
            <p className="notice">You can view investigations. Investigators and administrators can change them.</p>
          )}
        </article>
        <article className="card">
          <h2>Status history</h2>
          <ol className="timeline">
            {investigation.history.map((entry) => (
              <li key={`${entry.created_at}-${entry.to_status}`}>
                {entry.from_status ? `${humanise(entry.from_status)} to ` : "Opened as "}
                {humanise(entry.to_status)}, {formatDateTime(entry.created_at)}
                {entry.changed_by ? "" : " (by the system)"}
              </li>
            ))}
          </ol>
        </article>
      </div>
      <article className="card">
        <h2>Notes</h2>
        {investigation.notes.length === 0 ? (
          <p className="muted">No notes yet.</p>
        ) : (
          <ul className="notes">
            {investigation.notes.map((note) => (
              <li key={note.id}>
                <p>{note.note}</p>
                <span className="muted small">{formatDateTime(note.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
        {canUpdate ? <NoteForm onAdd={(text) => act(() => investigationsApi.addNote(id, text))} /> : null}
      </article>
    </section>
  );
}

function StatusControl({ current, onChange }: { current: string; onChange: (status: InvestigationUpdate["status"]) => Promise<void> }) {
  const [choice, setChoice] = useState(current);
  const [confirming, setConfirming] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (choice === current) return;
    if (CONCLUDING.has(choice)) setConfirming(true);
    else void onChange(choice as InvestigationUpdate["status"]);
  }

  return (
    <form onSubmit={submit}>
      <label htmlFor="new-status">Change status</label>
      <div className="inline-field">
        <select id="new-status" value={choice} onChange={(event) => setChoice(event.target.value)}>
          {STATUSES.map((value) => (
            <option key={value} value={value}>
              {humanise(value)}
            </option>
          ))}
        </select>
        <button type="submit" className="button primary" disabled={choice === current}>
          Update status
        </button>
      </div>
      <ConfirmDialog
        open={confirming}
        title={`Mark as ${humanise(choice).toLowerCase()}?`}
        message="This records a workflow outcome. It does not change the model's score or decision, and it is added to the status history."
        confirmLabel={`Mark as ${humanise(choice).toLowerCase()}`}
        onCancel={() => setConfirming(false)}
        onConfirm={() => {
          setConfirming(false);
          void onChange(choice as InvestigationUpdate["status"]);
        }}
      />
    </form>
  );
}

function AssigneeControl({ investigation, onChange }: { investigation: InvestigationDetail; onChange: (change: InvestigationUpdate) => Promise<void> }) {
  const { user } = useAuth();
  const assignees = useApiResource(() => usersApi.assignable(), []);
  const current = investigation.assigned_user_id;
  const currentEmail = assignees.data?.find((person) => person.id === current)?.email;

  return (
    <div className="assignee">
      <label htmlFor="assignee">Assigned to</label>
      <p className="muted small">{current ? currentEmail ?? "Someone who can no longer be assigned" : "Nobody"}</p>
      {assignees.error ? <ErrorState error={assignees.error} /> : null}
      <div className="inline-field">
        <select
          id="assignee"
          value={current ?? ""}
          onChange={(event) => void onChange({ assigned_user_id: event.target.value || null })}
        >
          <option value="">Nobody</option>
          {(assignees.data ?? []).map((person) => (
            <option key={person.id} value={person.id}>
              {person.email} ({humanise(person.role)})
            </option>
          ))}
        </select>
        {user && current !== user.id ? (
          <button type="button" className="button secondary" onClick={() => void onChange({ assigned_user_id: user.id })}>
            Assign to me
          </button>
        ) : null}
      </div>
    </div>
  );
}

function NoteForm({ onAdd }: { onAdd: (text: string) => Promise<void> }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const trimmed = text.trim();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!trimmed) return;
    setBusy(true);
    try {
      await onAdd(trimmed);
      setText("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)}>
      <label htmlFor="note">Add a note</label>
      <textarea id="note" value={text} maxLength={5000} onChange={(event) => setText(event.target.value)} />
      <p className="hint">{text.length} of 5,000 characters</p>
      <button type="submit" className="button primary" disabled={!trimmed || busy}>
        {busy ? "Saving…" : "Add note"}
      </button>
    </form>
  );
}
