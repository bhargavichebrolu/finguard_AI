/**
 * Reports (PRD 6.9): the four CSV downloads, for roles allowed to export.
 */
import { Download } from "lucide-react";
import { useState } from "react";

import { ErrorState, PageHeader } from "../components/feedback";
import { ApiError, toApiError } from "../services/api";
import { downloadFile, downloadPaths, type ReportType } from "../services/endpoints";

export const REPORTS: { type: ReportType; title: string; description: string }[] = [
  {
    type: "predictions",
    title: "Transaction predictions",
    description: "Every stored prediction in your scope, with its uncalibrated score, decision, model version and threshold. Labels are not included.",
  },
  {
    type: "flag_summary",
    title: "Flag summary",
    description: "Analysed and flagged counts by transaction type. Called a fraud summary in the PRD; it counts model flags, which are not findings of fraud.",
  },
  {
    type: "investigations",
    title: "Investigation summary",
    description: "Every investigation with its workflow status, assignee and the score that opened it.",
  },
  {
    type: "model_evaluation",
    title: "Model evaluation",
    description: "The saved Phase 2 validation and test results, including the false positive rate target. Nothing is recalculated.",
  },
];

export function ReportsPage() {
  const [busy, setBusy] = useState<ReportType | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  async function download(type: ReportType) {
    setBusy(type);
    setError(null);
    try {
      await downloadFile(downloadPaths.report(type), `finguard-${type}.csv`);
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section>
      <PageHeader title="Reports">Download records and saved results as CSV files.</PageHeader>
      {error ? <ErrorState error={error} /> : null}
      <div className="grid two">
        {REPORTS.map((report) => (
          <article key={report.type} className="card">
            <h2>{report.title}</h2>
            <p className="muted">{report.description}</p>
            <button type="button" className="button primary" onClick={() => void download(report.type)} disabled={busy !== null}>
              <Download aria-hidden="true" />
              {busy === report.type ? "Preparing…" : `Download ${report.title.toLowerCase()}`}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
