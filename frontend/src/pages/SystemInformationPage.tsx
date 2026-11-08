/**
 * System Information (PRD 7.4 page 10): service health, the frozen model's identity, and for
 * administrators the audit log.
 */
import { useState } from "react";

import { DataTable, Pager, type Column } from "../components/DataTable";
import { ErrorState, LoadingState, PageHeader } from "../components/feedback";
import { useApiResource } from "../hooks/useApiResource";
import { useAuth } from "../hooks/useAuth";
import { auditApi, systemApi, type AuditEntry } from "../services/endpoints";
import { formatDateTime, humanise } from "../utils/format";

const AUDIT_PAGE_SIZE = 20;

const AUDIT_COLUMNS: Column<AuditEntry>[] = [
  { key: "time", header: "Time", render: (row) => formatDateTime(row.created_at) },
  { key: "action", header: "Action", render: (row) => row.action },
  { key: "entity", header: "Record", render: (row) => humanise(row.entity_type) },
  { key: "user", header: "User", render: (row) => row.user_id ?? "System or unknown" },
];

export function SystemInformationPage() {
  const { can } = useAuth();
  const status = useApiResource(() => systemApi.status(), []);
  const health = useApiResource(() => systemApi.health(), []);

  return (
    <section>
      <PageHeader title="System Information">
        Live state of the API, the database and the frozen model.
      </PageHeader>
      <div className="grid two">
        <article className="card">
          <h2>Service</h2>
          {status.loading ? <LoadingState /> : null}
          {status.error ? <ErrorState error={status.error} onRetry={status.reload} /> : null}
          {status.data ? (
            <dl className="facts">
              <dt>Overall</dt>
              <dd>{status.data.status === "ok" ? "Working" : "Degraded"}</dd>
              <dt>API process</dt>
              <dd>{health.data?.status === "ok" ? "Responding" : health.error ? "Not responding" : "Checking"}</dd>
              <dt>Database</dt>
              <dd>{status.data.database_available ? "Available" : "Unavailable"}</dd>
              <dt>Application version</dt>
              <dd>{status.data.application_version}</dd>
              <dt>Environment</dt>
              <dd>{humanise(status.data.environment)}</dd>
            </dl>
          ) : null}
        </article>
        <article className="card">
          <h2>Frozen model</h2>
          {status.data ? (
            <dl className="facts">
              <dt>Model version</dt>
              <dd>{status.data.model_version}</dd>
              <dt>Review threshold</dt>
              <dd>
                {status.data.threshold} <span className="muted">(frozen; cannot be changed here)</span>
              </dd>
              <dt>File hash (SHA-256)</dt>
              <dd className="mono wrap">{status.data.model_sha256}</dd>
              <dt>Loaded</dt>
              <dd>{status.data.model_loaded ? "Verified and loaded at start-up" : "Not loaded"}</dd>
            </dl>
          ) : null}
        </article>
      </div>
      {can("view_audit_log") ? <AuditLog /> : null}
    </section>
  );
}

function AuditLog() {
  const [offset, setOffset] = useState(0);
  const log = useApiResource(() => auditApi.list(AUDIT_PAGE_SIZE, offset), [offset]);
  return (
    <article className="card">
      <h2>Audit log</h2>
      {log.loading ? <LoadingState /> : null}
      {log.error ? <ErrorState error={log.error} onRetry={log.reload} /> : null}
      {log.data ? (
        <>
          <DataTable
            caption="Audit log entries, newest first"
            columns={AUDIT_COLUMNS}
            rows={log.data.items}
            rowKey={(row) => row.id}
            emptyTitle="No audit entries yet"
          />
          <Pager total={log.data.total} limit={AUDIT_PAGE_SIZE} offset={offset} onChange={setOffset} />
        </>
      ) : null}
    </article>
  );
}
