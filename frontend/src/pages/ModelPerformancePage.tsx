/**
 * Model Performance (PRD 6.8). Every figure is copied from saved Phase 2 outputs through the
 * read-only report and metrics routes. Nothing is retrained or recalculated, and the test
 * partition is never read: test figures come from the single evaluation made after the freeze.
 */
import { useState } from "react";

import { CategoryBars, ChartCard, CurveChart } from "../components/charts";
import { DataTable, Pager, TableScroll, type Column } from "../components/DataTable";
import { ErrorState, LoadingState, PageHeader } from "../components/feedback";
import { ScoreDisclosure } from "../components/ScoreDisclosure";
import { useApiResource } from "../hooks/useApiResource";
import { modelsApi } from "../services/endpoints";
import {
  readReport,
  toPoints,
  type AtThreshold,
  type Confusion,
  type FamilyRow,
  type HistoryRow,
  type TypedReport,
} from "../types/report";
import { formatCount, formatRate, formatScore, humanise } from "../utils/format";

const HISTORY_PAGE_SIZE = 25;

/** Readable model family names. */
export function familyName(family: string): string {
  const names: Record<string, string> = {
    logistic_regression: "Logistic Regression",
    decision_tree: "Decision Tree",
    random_forest: "Random Forest",
    xgboost: "XGBoost",
    lightgbm: "LightGBM",
    catboost: "CatBoost",
  };
  return names[family] ?? humanise(family);
}

/** Readable names for the alternative threshold rules, such as "fpr_cap_0.001" or "max_f1". */
export function ruleName(rule: string): string {
  if (rule.startsWith("fpr_cap_")) return `False positive rate at most ${rule.slice("fpr_cap_".length)}`;
  if (rule.startsWith("max_")) return `Highest ${rule.slice("max_".length).toUpperCase()}`;
  return humanise(rule);
}

function decimal(value: number | null | undefined, digits = 4): string {
  return value === null || value === undefined ? "–" : value.toFixed(digits);
}

export function ModelPerformancePage() {
  const report = useApiResource(() => modelsApi.report(), []);
  return (
    <section>
      <PageHeader title="Model Performance">
        Saved results from the Phase 2 experiments. Validation results guided every choice; test
        results come from one evaluation after the model and threshold were frozen.
      </PageHeader>
      <ScoreDisclosure />
      {report.loading ? <LoadingState label="Loading saved results" /> : null}
      {report.error ? <ErrorState error={report.error} onRetry={report.reload} /> : null}
      {report.data ? <PerformanceContent report={readReport(report.data)} source={report.data.source_files} /> : null}
    </section>
  );
}

function PerformanceContent({ report, source }: { report: TypedReport; source: Record<string, string> }) {
  const { decision } = report;
  return (
    <>
      <article className="card">
        <h2>What these results show</h2>
        <ul>
          {report.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </article>
      <FamilyComparison families={report.families} decision={decision} />
      <CurveSection report={report} />
      <ConfusionSection confusion={report.confusion} />
      <ThresholdSection thresholds={report.thresholds} />
      <CostSection families={report.families} />
      <MatrixSection report={report} />
      <HistorySection history={report.history} />
      <article className="card">
        <h2>Sources</h2>
        <p className="muted small">Each value was copied from these saved files, whose SHA-256 hashes are recorded.</p>
        <ul className="small mono">
          {Object.entries(source).map(([path, hash]) => (
            <li key={path} className="wrap">
              {path}: {hash.slice(0, 16)}…
            </li>
          ))}
        </ul>
      </article>
    </>
  );
}

function FamilyComparison({ families, decision }: { families: FamilyRow[]; decision: TypedReport["decision"] }) {
  const tied = new Set(decision.statistically_indistinguishable);
  const columns: Column<FamilyRow>[] = [
    {
      key: "family",
      header: "Family",
      render: (row) => (
        <>
          {familyName(row.family)}
          {row.family === decision.selected_family ? <span className="badge badge-status">Selected</span> : null}
          {tied.has(row.family) && row.family !== decision.selected_family ? <span className="badge badge-neutral">Tied</span> : null}
        </>
      ),
    },
    { key: "strategy", header: "Strategy", render: (row) => humanise(row.strategy) },
    { key: "prauc", header: "PR-AUC", render: (row) => decimal(row.pr_auc), numeric: true },
    { key: "interval", header: "95% interval", render: (row) => `${decimal(row.pr_auc_interval.ci_low, 3)}–${decimal(row.pr_auc_interval.ci_high, 3)}` },
    { key: "roc", header: "ROC-AUC", render: (row) => decimal(row.roc_auc), numeric: true },
    { key: "precision", header: "Precision", render: (row) => formatRate(row.at_fpr_cap.precision), numeric: true },
    { key: "recall", header: "Recall", render: (row) => formatRate(row.at_fpr_cap.recall), numeric: true },
    { key: "f1", header: "F1", render: (row) => decimal(row.at_fpr_cap.f1, 3), numeric: true },
    { key: "bal", header: "Balanced accuracy", render: (row) => decimal(row.at_fpr_cap.balanced_accuracy, 3), numeric: true },
    { key: "fpr", header: "False positive rate", render: (row) => formatRate(row.at_fpr_cap.false_positive_rate, 3), numeric: true },
  ];
  return (
    <>
      <article className="card">
        <h2>Model comparison on validation</h2>
        <p className="muted small">
          Each family's best run. Threshold metrics use each model's own threshold at the validation
          false positive rate cap. {decision.statistically_indistinguishable.map(familyName).join(", ")} were
          statistically indistinguishable; {familyName(decision.selected_family)} was chosen by the pre-registered rule.
          Accuracy is not shown alone, because almost every row is legitimate.
        </p>
        <DataTable caption="Model comparison on validation" columns={columns} rows={families} rowKey={(row) => row.family} emptyTitle="No families" />
      </article>
      <ChartCard
        title="PR-AUC by family (validation)"
        description="Precision-recall area. The 95% intervals in the table overlap for the top three."
        tableColumns={[{ key: "label", header: "Family" }, { key: "value", header: "PR-AUC", numeric: true }]}
        tableRows={families.map((row) => ({ label: familyName(row.family), value: decimal(row.pr_auc) }))}
      >
        <CategoryBars
          data={families.map((row) => ({ label: familyName(row.family), value: row.pr_auc }))}
          valueLabel="PR-AUC"
          format={(value) => value.toFixed(2)}
        />
      </ChartCard>
    </>
  );
}

function CurveSection({ report }: { report: TypedReport }) {
  const families = Object.keys(report.familyCurves);
  const [family, setFamily] = useState(report.decision.selected_family);
  const selected = report.selectedCurves;
  const other = report.familyCurves[family];
  return (
    <>
      <h2 className="section-title">Curves</h2>
      <div className="grid two">
        <ChartCard
          title="Precision against recall: selected model"
          description="Validation and test. Test's higher precision partly reflects its higher fraud rate."
          tableColumns={[{ key: "set", header: "Partition" }, { key: "points", header: "Points", numeric: true }]}
          tableRows={[
            { set: "Validation", points: selected.validation.pr_recall.length },
            { set: "Test", points: selected.test.pr_recall.length },
          ]}
        >
          <CurveChart
            xLabel="Recall"
            yLabel="Precision"
            series={[
              { name: "Validation", points: toPoints(selected.validation.pr_recall, selected.validation.pr_precision) },
              { name: "Test", points: toPoints(selected.test.pr_recall, selected.test.pr_precision) },
            ]}
          />
        </ChartCard>
        <ChartCard
          title="ROC: selected model"
          tableColumns={[{ key: "set", header: "Partition" }, { key: "points", header: "Points", numeric: true }]}
          tableRows={[
            { set: "Validation", points: selected.validation.roc_fpr.length },
            { set: "Test", points: selected.test.roc_fpr.length },
          ]}
        >
          <CurveChart
            xLabel="False positive rate"
            yLabel="True positive rate"
            series={[
              { name: "Validation", points: toPoints(selected.validation.roc_fpr, selected.validation.roc_tpr) },
              { name: "Test", points: toPoints(selected.test.roc_fpr, selected.test.roc_tpr) },
            ]}
          />
        </ChartCard>
      </div>
      <article className="card">
        <label htmlFor="curve-family">Compare a family with the selected model on validation</label>
        <select id="curve-family" value={family} onChange={(event) => setFamily(event.target.value)}>
          {families.map((name) => (
            <option key={name} value={name}>
              {familyName(name)}
            </option>
          ))}
        </select>
      </article>
      {other ? (
        <ChartCard
          title={
            family === report.decision.selected_family
              ? `Precision against recall on validation: ${familyName(family)}`
              : `Precision against recall on validation: ${familyName(family)} and ${familyName(report.decision.selected_family)}`
          }
          tableColumns={[{ key: "name", header: "Family" }, { key: "points", header: "Points", numeric: true }]}
          tableRows={[{ name: familyName(family), points: other.pr_recall.length }]}
        >
          <CurveChart
            xLabel="Recall"
            yLabel="Precision"
            series={[
              { name: familyName(report.decision.selected_family), points: toPoints(selected.validation.pr_recall, selected.validation.pr_precision) },
              ...(family === report.decision.selected_family ? [] : [{ name: familyName(family), points: toPoints(other.pr_recall, other.pr_precision) }]),
            ]}
          />
        </ChartCard>
      ) : null}
    </>
  );
}

function ConfusionTable({ title, values }: { title: string; values: Confusion }) {
  return (
    <article className="card">
      <h3>{title}</h3>
      <TableScroll label={title}>
      <table className="data-table">
        <caption className="visually-hidden">{title}</caption>
        <thead>
          <tr>
            <th scope="col">Label</th>
            <th scope="col" className="numeric">Flagged</th>
            <th scope="col" className="numeric">Not flagged</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Labelled fraud</th>
            <td className="numeric">{formatCount(values.true_positives)}</td>
            <td className="numeric">{formatCount(values.false_negatives)}</td>
          </tr>
          <tr>
            <th scope="row">Labelled legitimate</th>
            <td className="numeric">{formatCount(values.false_positives)}</td>
            <td className="numeric">{formatCount(values.true_negatives)}</td>
          </tr>
        </tbody>
      </table>
      </TableScroll>
    </article>
  );
}

function ConfusionSection({ confusion }: { confusion: TypedReport["confusion"] }) {
  return (
    <>
      <h2 className="section-title">Confusion matrices at the frozen threshold</h2>
      <div className="grid two">
        <ConfusionTable title="Validation" values={confusion.validation} />
        <ConfusionTable title="Test, evaluated once" values={confusion.test} />
        {Object.entries(confusion.test_by_step_type).map(([name, values]) => (
          <ConfusionTable key={name} title={`Test, ${name} steps`} values={values} />
        ))}
      </div>
    </>
  );
}

function ThresholdSection({ thresholds }: { thresholds: TypedReport["thresholds"] }) {
  const rows: { name: string; values: AtThreshold }[] = [
    { name: "Frozen threshold", values: thresholds.selected },
    ...Object.entries(thresholds.rule_alternatives).map(([name, values]) => ({ name: ruleName(name), values })),
    ...Object.entries(thresholds.prd_candidates).map(([name, values]) => ({ name: `PRD candidate ${name}`, values })),
  ];
  const columns: Column<{ name: string; values: AtThreshold }>[] = [
    { key: "name", header: "Rule", render: (row) => row.name },
    { key: "threshold", header: "Threshold", render: (row) => formatScore(row.values.threshold), numeric: true },
    { key: "precision", header: "Precision", render: (row) => formatRate(row.values.precision), numeric: true },
    { key: "recall", header: "Recall", render: (row) => formatRate(row.values.recall), numeric: true },
    { key: "fpr", header: "False positive rate", render: (row) => formatRate(row.values.false_positive_rate, 3), numeric: true },
    { key: "alerts", header: "Alerts", render: (row) => formatCount(row.values.alerts), numeric: true },
  ];
  const sweep = thresholds.sweep.filter((row) => row.threshold > 0);
  return (
    <>
      <h2 className="section-title">Threshold comparison (validation)</h2>
      <article className="card">
        <p className="muted small">{thresholds.objective} Other rules are shown for comparison only; the frozen threshold was not changed.</p>
        <DataTable caption="Thresholds compared on validation" columns={columns} rows={rows} rowKey={(row) => row.name} emptyTitle="No thresholds" />
      </article>
      <ChartCard
        title="Precision and recall across thresholds (validation)"
        description="Threshold on a log scale. Precision and recall share one axis because both are proportions."
        tableColumns={[
          { key: "threshold", header: "Threshold", numeric: true },
          { key: "precision", header: "Precision", numeric: true },
          { key: "recall", header: "Recall", numeric: true },
        ]}
        tableRows={sweep.map((row) => ({
          threshold: row.threshold.toPrecision(3),
          precision: formatRate(row.precision),
          recall: formatRate(row.recall),
        }))}
      >
        <CurveChart
          logX
          xLabel="Threshold"
          yLabel="Proportion"
          series={[
            { name: "Precision", points: sweep.map((row) => ({ x: row.threshold, y: row.precision })) },
            { name: "Recall", points: sweep.map((row) => ({ x: row.threshold, y: row.recall })) },
          ]}
        />
      </ChartCard>
    </>
  );
}

function CostSection({ families }: { families: FamilyRow[] }) {
  return (
    <div className="grid two">
      <ChartCard
        title="Training time (seconds)"
        tableColumns={[{ key: "label", header: "Family" }, { key: "value", header: "Seconds", numeric: true }]}
        tableRows={families.map((row) => ({ label: familyName(row.family), value: row.training_seconds.toFixed(1) }))}
      >
        <CategoryBars data={families.map((row) => ({ label: familyName(row.family), value: row.training_seconds }))} valueLabel="Seconds" />
      </ChartCard>
      <ChartCard
        title="Inference time for one transaction (milliseconds)"
        description="Median single-row time recorded during the experiments."
        tableColumns={[
          { key: "label", header: "Family" },
          { key: "value", header: "Single row (ms)", numeric: true },
          { key: "batch", header: "Batch (µs per row)", numeric: true },
        ]}
        tableRows={families.map((row) => ({
          label: familyName(row.family),
          value: row.single_row_ms.toFixed(2),
          batch: row.batch_microseconds_per_row.toFixed(2),
        }))}
      >
        <CategoryBars
          data={families.map((row) => ({ label: familyName(row.family), value: row.single_row_ms }))}
          valueLabel="Milliseconds"
          format={(value) => value.toFixed(1)}
        />
      </ChartCard>
    </div>
  );
}

function MatrixSection({ report }: { report: TypedReport }) {
  const strategies = Array.from(new Set(report.matrix.map((cell) => cell.strategy)));
  const families = Array.from(new Set(report.matrix.map((cell) => cell.family)));
  const lookup = new Map(report.matrix.map((cell) => [`${cell.family}|${cell.strategy}`, cell]));
  return (
    <article className="card">
      <h2>Imbalance strategies: PR-AUC on validation</h2>
      <p className="muted small">
        Baseline settings for every family and strategy. LightGBM's original and class-weighted results
        reflect a numerical divergence during fitting, not those strategies.
      </p>
      <TableScroll label="PR-AUC by family and imbalance strategy">
        <table className="data-table">
          <caption className="visually-hidden">PR-AUC by family and imbalance strategy</caption>
          <thead>
            <tr>
              <th scope="col">Family</th>
              {strategies.map((strategy) => (
                <th key={strategy} scope="col" className="numeric">
                  {humanise(strategy)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {families.map((family) => (
              <tr key={family}>
                <th scope="row">{familyName(family)}</th>
                {strategies.map((strategy) => (
                  <td key={strategy} className="numeric">
                    {decimal(lookup.get(`${family}|${strategy}`)?.pr_auc)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </TableScroll>
    </article>
  );
}

function HistorySection({ history }: { history: HistoryRow[] }) {
  const stages = Array.from(new Set(history.map((row) => row.stage)));
  const [stage, setStage] = useState("");
  const [offset, setOffset] = useState(0);
  const rows = stage ? history.filter((row) => row.stage === stage) : history;
  const columns: Column<HistoryRow>[] = [
    { key: "run", header: "Run", render: (row) => <span className="mono">{row.run_id}</span> },
    { key: "stage", header: "Stage", render: (row) => humanise(row.stage) },
    { key: "family", header: "Family", render: (row) => familyName(row.family) },
    { key: "strategy", header: "Strategy", render: (row) => humanise(row.strategy) },
    { key: "seed", header: "Seed", render: (row) => row.seed ?? "–", numeric: true },
    { key: "prauc", header: "PR-AUC", render: (row) => decimal(row.pr_auc), numeric: true },
    { key: "recall", header: "Recall at FPR cap", render: (row) => formatRate(row.fpr_cap_recall), numeric: true },
    { key: "time", header: "Training (s)", render: (row) => decimal(row.total_training_seconds, 1), numeric: true },
  ];
  return (
    <article className="card">
      <h2>Experiment history</h2>
      <p className="muted small">All {formatCount(history.length)} recorded runs, on validation data.</p>
      <label htmlFor="history-stage">Stage</label>
      <select id="history-stage" value={stage} onChange={(event) => { setStage(event.target.value); setOffset(0); }}>
        <option value="">All stages</option>
        {stages.map((name) => (
          <option key={name} value={name}>
            {humanise(name)}
          </option>
        ))}
      </select>
      <DataTable
        caption="Recorded experiment runs"
        columns={columns}
        rows={rows.slice(offset, offset + HISTORY_PAGE_SIZE)}
        rowKey={(row) => row.run_id}
        emptyTitle="No runs at this stage"
      />
      <Pager total={rows.length} limit={HISTORY_PAGE_SIZE} offset={offset} onChange={setOffset} />
    </article>
  );
}
