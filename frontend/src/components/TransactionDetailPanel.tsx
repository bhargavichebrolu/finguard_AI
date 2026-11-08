/**
 * Everything PRD 6.6 lists for one transaction: attributes, score, model version, explanation,
 * investigation status, notes and status history.
 */
import { Link } from "react-router-dom";

import { useApiResource } from "../hooks/useApiResource";
import { transactionsApi } from "../services/endpoints";
import { formatDateTime, humanise } from "../utils/format";
import { StatusBadge } from "./badges";
import { ExplanationPanel } from "./ExplanationPanel";
import { ErrorState, LoadingState } from "./feedback";
import { PredictionResult } from "./PredictionResult";

export function TransactionDetailPanel({ transactionId, onClose }: { transactionId: string; onClose: () => void }) {
  const detail = useApiResource(() => transactionsApi.get(transactionId), [transactionId]);
  if (detail.loading) return <LoadingState label="Loading the transaction" />;
  if (detail.error) return <ErrorState error={detail.error} onRetry={detail.reload} />;
  if (!detail.data) return null;
  const transaction = detail.data;
  const investigation = transaction.investigation;

  return (
    <section className="detail-panel" aria-label="Transaction detail">
      <div className="detail-header">
        <h2>Transaction {transaction.external_transaction_id}</h2>
        <button type="button" className="button secondary" onClick={onClose}>
          Close
        </button>
      </div>
      <PredictionResult prediction={transaction} />
      <article className="card">
        <h2>Investigation</h2>
        {investigation ? (
          <>
            <p>
              <StatusBadge status={investigation.status} />{" "}
              <span className="muted small">Workflow label, not a verified finding.</span>
            </p>
            <h3>Status history</h3>
            <ol className="timeline">
              {investigation.history.map((entry) => (
                <li key={`${entry.created_at}-${entry.to_status}`}>
                  {entry.from_status ? `${humanise(entry.from_status)} to ` : "Opened as "}
                  {humanise(entry.to_status)}, {formatDateTime(entry.created_at)}
                </li>
              ))}
            </ol>
            <h3>Notes</h3>
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
            <p>
              <Link to={`/investigations?open=${investigation.id}`}>Open in the Investigation Centre</Link>
            </p>
          </>
        ) : (
          <p className="muted">
            No investigation. Investigations open only for flagged transactions that are not demo records.
          </p>
        )}
      </article>
      <ExplanationPanel explanation={transaction.explanation} />
    </section>
  );
}
