/**
 * Dashboard (PRD 6.1). Model flags, investigation workflow and uploaded labels are separate
 * sections, because PRD 6.1 forbids mixing them. Every figure comes from the API.
 */
import { Link } from "react-router-dom";

import { DecisionBadge, RiskBadge } from "../components/badges";
import { CategoryBars, ChartCard, PairedBars, StatTile, TrendLine } from "../components/charts";
import { DataTable, type Column } from "../components/DataTable";
import { ErrorState, LoadingState, PageHeader } from "../components/feedback";
import { ScoreDisclosure } from "../components/ScoreDisclosure";
import { useApiResource } from "../hooks/useApiResource";
import { useModelLimits } from "../hooks/useModelLimits";
import { reportsApi, type SummaryReport, type TransactionSummary } from "../services/endpoints";
import { formatAmount, formatCount, formatDateTime, formatRate, formatScore, humanise } from "../utils/format";

const RISK_ORDER = ["LOW", "MEDIUM", "HIGH"];

const RECENT_COLUMNS: Column<TransactionSummary>[] = [
  { key: "id", header: "Transaction", render: (row) => row.external_transaction_id },
  { key: "type", header: "Type", render: (row) => humanise(row.transaction_type) },
  { key: "amount", header: "Amount", render: (row) => formatAmount(row.amount), numeric: true },
  { key: "score", header: "Model score", render: (row) => formatScore(row.model_score), numeric: true },
  { key: "risk", header: "Risk", render: (row) => <RiskBadge level={row.risk_level} /> },
  { key: "decision", header: "Decision", render: (row) => <DecisionBadge decision={row.prediction} /> },
  { key: "time", header: "Scored", render: (row) => formatDateTime(row.created_at) },
];

export function DashboardPage() {
  const summary = useApiResource(() => reportsApi.summary(), []);
  return (
    <section>
      <PageHeader title="Dashboard">
        What the model has flagged in your records, what reviewers have recorded, and how the model
        performed when it was evaluated.
      </PageHeader>
      <ScoreDisclosure compact />
      {summary.loading ? <LoadingState /> : null}
      {summary.error ? <ErrorState error={summary.error} onRetry={summary.reload} /> : null}
      {summary.data ? <DashboardContent summary={summary.data} /> : null}
    </section>
  );
}

function DashboardContent({ summary }: { summary: SummaryReport }) {
  const flags = summary.model_flags;
  const risk = RISK_ORDER.map((level) => ({ label: humanise(level), value: flags.risk_distribution[level] ?? 0 }));
  const types = Object.entries(flags.type_distribution).map(([name, counts]) => ({
    label: humanise(name),
    first: counts.analysed ?? 0,
    second: counts.flagged ?? 0,
  }));
  const days = flags.flags_by_simulation_day.map((row) => ({ x: row.day, y: row.flagged, analysed: row.analysed }));

  return (
    <>
      <p className="notice" role="note">
        {summary.is_demo ? "Demo scope: synthetic sample records only. " : null}
        {summary.note}
      </p>

      <h2 className="section-title">Model flags</h2>
      <div className="grid four">
        <StatTile label="Transactions analysed" value={formatCount(flags.total_analysed)} />
        <StatTile label="Flagged for review" value={formatCount(flags.flagged_for_review)} />
        <StatTile label="Not flagged" value={formatCount(flags.not_flagged)} />
        <StatTile label="Share flagged" value={formatRate(flags.flag_rate)} note="Of analysed records; not a fraud rate" />
        <StatTile label="Total value analysed" value={formatAmount(flags.total_value)} />
        <StatTile label="Value flagged for review" value={formatAmount(flags.flagged_value)} />
      </div>
      {flags.total_analysed === 0 ? (
        <p className="muted">No transactions have been analysed in this scope yet.</p>
      ) : (
        <div className="grid two">
          <ChartCard
            title="Risk bands"
            description="Low means not flagged. Medium and High are both flagged for review."
            tableColumns={[{ key: "label", header: "Risk band" }, { key: "value", header: "Transactions", numeric: true }]}
            tableRows={risk.map((row) => ({ label: row.label, value: formatCount(row.value) }))}
          >
            <CategoryBars data={risk} valueLabel="Transactions" />
          </ChartCard>
          <ChartCard
            title="Analysed and flagged by type"
            tableColumns={[
              { key: "label", header: "Type" },
              { key: "first", header: "Analysed", numeric: true },
              { key: "second", header: "Flagged for review", numeric: true },
            ]}
            tableRows={types.map((row) => ({ label: row.label, first: formatCount(row.first), second: formatCount(row.second) }))}
          >
            <PairedBars data={types} firstLabel="Analysed" secondLabel="Flagged for review" />
          </ChartCard>
          <ChartCard
            title="Flagged for review per simulated day"
            description="A simulated day is 24 PaySim steps. Counts reflect what was submitted, not fraud trends in the world."
            tableColumns={[
              { key: "x", header: "Simulated day", numeric: true },
              { key: "analysed", header: "Analysed", numeric: true },
              { key: "y", header: "Flagged for review", numeric: true },
            ]}
            tableRows={days.map((row) => ({ x: row.x, analysed: formatCount(row.analysed), y: formatCount(row.y) }))}
          >
            <TrendLine data={days} xLabel="Simulated day" yLabel="Flagged for review" />
          </ChartCard>
        </div>
      )}

      <div className="grid two">
        <article className="card">
          <h2>Investigation workflow</h2>
          <p className="muted small">What reviewers have recorded. These are workflow labels, not verified findings.</p>
          {Object.keys(summary.investigation_workflow.status_counts).length === 0 ? (
            <p className="muted">No investigations yet.</p>
          ) : (
            <dl className="facts">
              {Object.entries(summary.investigation_workflow.status_counts).map(([status, count]) => (
                <div key={status} className="fact-row">
                  <dt>{humanise(status)}</dt>
                  <dd>{formatCount(count)}</dd>
                </div>
              ))}
            </dl>
          )}
        </article>
        <article className="card">
          <h2>Uploaded labels</h2>
          <p className="muted small">Labels supplied with CSV uploads. They were never used to score anything.</p>
          {summary.uploaded_labels.labelled_rows === 0 ? (
            <p className="muted">No labels have been supplied.</p>
          ) : (
            <dl className="facts">
              <dt>Labelled rows</dt>
              <dd>{formatCount(summary.uploaded_labels.labelled_rows)}</dd>
              <dt>Labelled as fraud</dt>
              <dd>{formatCount(summary.uploaded_labels.labelled_fraud_rows)}</dd>
              <dt>Value labelled as fraud</dt>
              <dd>{formatAmount(summary.uploaded_labels.labelled_fraud_value)}</dd>
            </dl>
          )}
        </article>
      </div>

      <ModelPerformanceSummary />

      <article className="card">
        <h2>Recent activity</h2>
        <DataTable
          caption="Most recent predictions"
          columns={RECENT_COLUMNS}
          rows={summary.recent_activity}
          rowKey={(row) => row.transaction_id}
          emptyTitle="No predictions yet"
          emptyMessage="Score a transaction or upload a CSV to see activity here."
        />
      </article>
    </>
  );
}

function ModelPerformanceSummary() {
  const { metrics } = useModelLimits();
  if (!metrics) return null;
  const test = metrics.test.at_frozen_threshold;
  const normal = metrics.test.regimes.normal?.at_frozen_threshold;
  return (
    <article className="card">
      <h2>Model performance summary</h2>
      <p className="muted small">
        Measured once on the test partition after the model and threshold were frozen. Source: {metrics.source}.
      </p>
      <div className="grid four">
        <StatTile label="Labelled fraud flagged (recall)" value={formatRate(test.recall)} />
        <StatTile label="Recall in normal steps" value={normal ? formatRate(normal.recall) : "–"} />
        <StatTile label="Flags that were labelled fraud (precision)" value={formatRate(test.precision)} />
        <StatTile
          label="False positive rate"
          value={formatRate(test.false_positive_rate, 3)}
          note={`Target was ${formatRate(metrics.threshold.operational_fpr_cap, 1)}`}
        />
      </div>
      <p>
        <Link to="/models">Full model performance</Link>
      </p>
    </article>
  );
}
