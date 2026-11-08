/**
 * CSV Batch Analysis (PRD 6.4): upload a file, watch it process, then review, download and fix.
 * The browser checks type and size against the API's own limits; the API checks everything again.
 */
import { useEffect, useState, type ChangeEvent } from "react";

import { DecisionBadge, RiskBadge } from "../components/badges";
import { DataTable, Pager, type Column } from "../components/DataTable";
import { ErrorState, LoadingState, PageHeader } from "../components/feedback";
import { ScoreDisclosure } from "../components/ScoreDisclosure";
import { useApiResource, usePolling } from "../hooks/useApiResource";
import { ApiError, toApiError } from "../services/api";
import {
  batchesApi,
  downloadFile,
  downloadPaths,
  settingsApi,
  type Batch,
  type TransactionSummary,
} from "../services/endpoints";
import { formatAmount, formatCount, formatDateTime, formatScore, humanise } from "../utils/format";

const RESULTS_PAGE_SIZE = 25;
const POLL_INTERVAL_MS = 1000;
const FINISHED = new Set(["COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"]);
const TEMPLATE =
  "external_transaction_id,amount,transaction_type,step,destination_category\n" +
  "EXAMPLE-1,181.00,TRANSFER,1,customer\n" +
  "EXAMPLE-2,9.99,PAYMENT,2,merchant\n";

/** Refuse a file the API would refuse, before uploading it. Returns a message, or null. */
export function checkFile(file: File, maxBytes: number): string | null {
  if (!file.name.toLowerCase().endsWith(".csv")) return "Choose a .csv file.";
  if (file.size === 0) return "The file is empty.";
  if (file.size > maxBytes) return `The file is larger than the ${formatCount(maxBytes)} byte limit.`;
  return null;
}

const RESULT_COLUMNS: Column<TransactionSummary>[] = [
  { key: "id", header: "Transaction", render: (row) => row.external_transaction_id },
  { key: "type", header: "Type", render: (row) => humanise(row.transaction_type) },
  { key: "amount", header: "Amount", render: (row) => formatAmount(row.amount), numeric: true },
  { key: "step", header: "Step", render: (row) => row.step, numeric: true },
  { key: "score", header: "Model score", render: (row) => formatScore(row.model_score), numeric: true },
  { key: "risk", header: "Risk", render: (row) => <RiskBadge level={row.risk_level} /> },
  { key: "decision", header: "Decision", render: (row) => <DecisionBadge decision={row.prediction} /> },
];

const BATCH_COLUMNS: Column<Batch>[] = [
  { key: "file", header: "File", render: (row) => row.filename },
  { key: "status", header: "Status", render: (row) => humanise(row.status) },
  { key: "rows", header: "Rows", render: (row) => formatCount(row.total_records), numeric: true },
  { key: "failed", header: "Refused", render: (row) => formatCount(row.failed_records), numeric: true },
  { key: "time", header: "Uploaded", render: (row) => formatDateTime(row.created_at) },
];

export function BatchAnalysisPage() {
  const settings = useApiResource(() => settingsApi.get(), []);
  const recent = useApiResource(() => batchesApi.list(10, 0), []);
  const [file, setFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<ApiError | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  // Worked out on every render, not when the file is chosen: a file chosen before the upload
  // limits had loaded used to skip the check and could then be uploaded.
  const fileError = file && settings.data ? checkFile(file, settings.data.max_upload_bytes) : null;

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setUploadError(null);
  }

  async function upload() {
    if (!file || fileError) return;
    setUploadError(null);
    setProgress(0);
    try {
      const job = await batchesApi.upload(file, setProgress);
      setJobId(job.id);
      recent.reload();
    } catch (caught) {
      setUploadError(toApiError(caught));
    } finally {
      setProgress(null);
    }
  }

  function downloadTemplate() {
    const url = URL.createObjectURL(new Blob([TEMPLATE], { type: "text/csv" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "finguard-template.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section>
      <PageHeader title="CSV Batch Analysis">
        Score many simulated transactions at once. Required columns: amount, transaction_type,
        step and destination_category, with an optional external_transaction_id. An isFraud column
        is accepted but never used for scoring; balance and account columns are refused.
      </PageHeader>
      <ScoreDisclosure compact />
      <div className="grid two">
        <article className="card">
          <h2>Upload</h2>
          {settings.loading ? <LoadingState label="Loading upload limits" /> : null}
          {settings.error ? <ErrorState error={settings.error} onRetry={settings.reload} /> : null}
          {settings.data ? (
            <p className="muted small">
              Up to {formatCount(settings.data.max_upload_bytes)} bytes and {formatCount(settings.data.max_batch_rows)} rows.
            </p>
          ) : null}
          <label htmlFor="csv-file">CSV file</label>
          <input id="csv-file" type="file" accept=".csv,text/csv" onChange={chooseFile} />
          {fileError ? (
            <p className="error-text" role="alert">
              {fileError}
            </p>
          ) : null}
          {progress !== null ? (
            <div className="progress-row">
              <label htmlFor="upload-progress">Uploading</label>
              <progress id="upload-progress" max={1} value={progress} />
            </div>
          ) : null}
          {uploadError ? <ErrorState error={uploadError} /> : null}
          <div className="button-row">
            <button
              type="button"
              className="button primary"
              onClick={() => void upload()}
              disabled={!file || Boolean(fileError) || progress !== null || !settings.data}
            >
              Upload and score
            </button>
            <button type="button" className="button secondary" onClick={downloadTemplate}>
              Download a template
            </button>
          </div>
        </article>
        <article className="card">
          <h2>Recent uploads</h2>
          {recent.error ? <ErrorState error={recent.error} onRetry={recent.reload} /> : null}
          {recent.data ? (
            <DataTable
              caption="Recent batch uploads"
              columns={BATCH_COLUMNS}
              rows={recent.data.items}
              rowKey={(row) => row.id}
              emptyTitle="No uploads yet"
              onRowSelect={(row) => setJobId(row.id)}
              selectedKey={jobId}
            />
          ) : null}
        </article>
      </div>
      {jobId ? <BatchJobView key={jobId} jobId={jobId} onFinished={recent.reload} /> : null}
    </section>
  );
}

function BatchJobView({ jobId, onFinished }: { jobId: string; onFinished: () => void }) {
  const job = useApiResource(() => batchesApi.get(jobId), [jobId]);
  const status = job.data?.status;
  const running = Boolean(status) && !FINISHED.has(status as string);
  usePolling(job.reload, POLL_INTERVAL_MS, running);
  const [downloadError, setDownloadError] = useState<ApiError | null>(null);
  const finished = Boolean(status) && FINISHED.has(status as string);

  // Refresh the recent uploads list once, when this job reaches a final status.
  useEffect(() => {
    if (finished) onFinished();
  }, [finished, onFinished]);

  async function download(path: string, name: string) {
    setDownloadError(null);
    try {
      await downloadFile(path, name);
    } catch (caught) {
      setDownloadError(toApiError(caught));
    }
  }

  if (!job.data) {
    return job.error ? <ErrorState error={job.error} onRetry={job.reload} /> : <LoadingState />;
  }
  const data = job.data;
  return (
    <>
      <article className="card" aria-label="Batch status">
        <h2>{data.filename}</h2>
        <div className="progress-row">
          <label htmlFor="processing-progress">
            {humanise(data.status)}: {formatCount(data.processed_records)} of {formatCount(data.total_records)} rows
          </label>
          <progress id="processing-progress" max={100} value={data.progress_percent} />
        </div>
        <dl className="facts">
          <dt>Scored and stored</dt>
          <dd>{formatCount(data.succeeded_records)}</dd>
          <dt>Refused</dt>
          <dd>{formatCount(data.failed_records)}</dd>
          <dt>Ignored columns</dt>
          <dd>
            {data.ignored_columns.length > 0
              ? `${data.ignored_columns.join(", ")}: kept out of scoring`
              : "None"}
          </dd>
          <dt>Labels supplied</dt>
          <dd>{data.labels_supplied ? "Yes, stored separately and never used to score" : "No"}</dd>
          {data.is_demo ? (
            <>
              <dt>Records</dt>
              <dd>Synthetic demo records</dd>
            </>
          ) : null}
        </dl>
        {data.error_message ? (
          <p className="error-text" role="alert">
            {data.error_message}
          </p>
        ) : null}
        {downloadError ? <ErrorState error={downloadError} /> : null}
        {FINISHED.has(data.status) ? (
          <div className="button-row">
            <button
              type="button"
              className="button secondary"
              onClick={() => void download(downloadPaths.batchResults(data.id), "batch-results.csv")}
            >
              Download results
            </button>
            {data.failed_records > 0 ? (
              <button
                type="button"
                className="button secondary"
                onClick={() => void download(downloadPaths.batchErrors(data.id), "batch-errors.csv")}
              >
                Download error report
              </button>
            ) : null}
          </div>
        ) : null}
      </article>
      {FINISHED.has(data.status) ? <BatchResults jobId={data.id} /> : null}
    </>
  );
}

function BatchResults({ jobId }: { jobId: string }) {
  const [offset, setOffset] = useState(0);
  const results = useApiResource(() => batchesApi.results(jobId, RESULTS_PAGE_SIZE, offset), [jobId, offset]);
  return (
    <article className="card">
      <h2>Results, highest score first</h2>
      {results.loading ? <LoadingState /> : null}
      {results.error ? <ErrorState error={results.error} onRetry={results.reload} /> : null}
      {results.data ? (
        <>
          <DataTable
            caption="Batch results"
            columns={RESULT_COLUMNS}
            rows={results.data.items}
            rowKey={(row) => row.transaction_id}
            emptyTitle="No rows were stored"
            emptyMessage="Every row was refused. Download the error report to see why."
          />
          <Pager total={results.data.total} limit={RESULTS_PAGE_SIZE} offset={offset} onChange={setOffset} />
        </>
      ) : null}
    </article>
  );
}
