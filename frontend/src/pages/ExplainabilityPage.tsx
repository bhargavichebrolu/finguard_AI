/**
 * Explainable AI (PRD 7.4 page 7): saved global importance from Phase 2, and the stored
 * explanation of any recent prediction. Explanations describe the model, not what causes fraud.
 */
import { useState } from "react";

import { DecisionBadge } from "../components/badges";
import { CategoryBars, ChartCard } from "../components/charts";
import { DataTable, type Column } from "../components/DataTable";
import { ExplanationPanel, featureLabel } from "../components/ExplanationPanel";
import { ErrorState, LoadingState, PageHeader } from "../components/feedback";
import { useApiResource } from "../hooks/useApiResource";
import { modelsApi, transactionsApi, type TransactionSummary } from "../services/endpoints";
import { formatScore, humanise } from "../utils/format";

const GROUP_LABELS: Record<string, string> = {
  amount: "Amount",
  hour: "Hour of day",
  transaction_type_and_destination: "Type and destination",
};

const RECENT_COLUMNS: Column<TransactionSummary>[] = [
  { key: "id", header: "Transaction", render: (row) => row.external_transaction_id },
  { key: "type", header: "Type", render: (row) => humanise(row.transaction_type) },
  { key: "score", header: "Model score", render: (row) => formatScore(row.model_score), numeric: true },
  { key: "decision", header: "Decision", render: (row) => <DecisionBadge decision={row.prediction} /> },
];

export function ExplainabilityPage() {
  const importance = useApiResource(() => modelsApi.featureImportance(), []);
  return (
    <section>
      <PageHeader title="Explainable AI">
        How the model's output depends on its inputs, from TreeSHAP values. These describe the
        model's behaviour and do not show what causes fraud.
      </PageHeader>
      {importance.loading ? <LoadingState /> : null}
      {importance.error ? <ErrorState error={importance.error} onRetry={importance.reload} /> : null}
      {importance.data ? (
        <>
          <div className="grid two">
            <ChartCard
              title="Overall importance by input group"
              description={`Mean absolute contribution (${importance.data.output_scale.replace("_", "-")}), from the saved Phase 2 analysis on validation data.`}
              tableColumns={[{ key: "label", header: "Input group" }, { key: "value", header: "Mean absolute contribution", numeric: true }]}
              tableRows={Object.entries(importance.data.by_group).map(([name, value]) => ({
                label: GROUP_LABELS[name] ?? humanise(name),
                value: value.toFixed(3),
              }))}
            >
              <CategoryBars
                data={Object.entries(importance.data.by_group).map(([name, value]) => ({ label: GROUP_LABELS[name] ?? humanise(name), value }))}
                valueLabel="Mean absolute contribution"
              />
            </ChartCard>
            <article className="card">
              <h2>By model input</h2>
              <div className="table-wrap">
                <table className="data-table">
                  <caption className="visually-hidden">Mean absolute contribution of each model input</caption>
                  <thead>
                    <tr>
                      <th scope="col">Model input</th>
                      <th scope="col" className="numeric">Mean absolute contribution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(importance.data.by_feature)
                      .sort((a, b) => b[1] - a[1])
                      .map(([name, value]) => (
                        <tr key={name}>
                          <td>{featureLabel(name)}</td>
                          <td className="numeric">{value.toFixed(3)}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </article>
          </div>
          <article className="card">
            <h2>Limits</h2>
            <ul>
              {importance.data.limitations.map((limit) => (
                <li key={limit}>{limit}</li>
              ))}
            </ul>
          </article>
        </>
      ) : null}
      <LocalExplanations />
    </section>
  );
}

function LocalExplanations() {
  const [selected, setSelected] = useState<string | null>(null);
  const recent = useApiResource(() => transactionsApi.list({ limit: 10, sort_by: "created_at", sort_order: "desc" }), []);
  const detail = useApiResource(
    () => (selected ? transactionsApi.get(selected) : Promise.resolve(null)),
    [selected],
  );
  return (
    <>
      <article className="card">
        <h2>Explain a recent prediction</h2>
        {recent.loading ? <LoadingState /> : null}
        {recent.error ? <ErrorState error={recent.error} onRetry={recent.reload} /> : null}
        {recent.data ? (
          <DataTable
            caption="Recent predictions to explain"
            columns={RECENT_COLUMNS}
            rows={recent.data.items}
            rowKey={(row) => row.transaction_id}
            emptyTitle="No predictions yet"
            emptyMessage="Score a transaction first."
            onRowSelect={(row) => setSelected(row.transaction_id)}
            selectedKey={selected}
          />
        ) : null}
      </article>
      {selected && detail.loading ? <LoadingState label="Loading the explanation" /> : null}
      {detail.error ? <ErrorState error={detail.error} /> : null}
      {detail.data ? <ExplanationPanel explanation={detail.data.explanation} /> : null}
    </>
  );
}
