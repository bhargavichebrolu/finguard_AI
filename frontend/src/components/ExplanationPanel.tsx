/**
 * Shows how each input moved one score, with the limits of what that means (PRD 5.7, 6.6).
 */
import type { Prediction } from "../services/endpoints";
import { humanise } from "../utils/format";
import { ChartCard, ContributionBars } from "./charts";

type Explanation = NonNullable<Prediction["explanation"]>;

const GROUP_LABELS: Record<string, string> = {
  amount: "Amount",
  hour: "Hour of day (from step)",
  transaction_type_and_destination: "Type and destination",
};

/** Readable names for the model's encoded inputs, such as transaction_type_TRANSFER. */
export function featureLabel(name: string): string {
  if (name.startsWith("transaction_type_")) return `Type is ${name.replace("transaction_type_", "")}`;
  if (name.startsWith("destination_category_")) return `Destination is ${name.replace("destination_category_", "")}`;
  const known: Record<string, string> = {
    amount: "Amount",
    amount_log1p: "Amount (log scale)",
    hour_of_day: "Hour of day",
    hour_sin: "Hour of day (sine)",
    hour_cos: "Hour of day (cosine)",
  };
  return known[name] ?? humanise(name);
}

export function ExplanationPanel({ explanation }: { explanation: Explanation | null | undefined }) {
  if (!explanation) {
    return (
      <article className="card">
        <h2>Explanation</h2>
        <p className="muted">
          No explanation is stored for this transaction. Single predictions always have one; batch
          rows have one only when they were flagged for review.
        </p>
      </article>
    );
  }
  const groups = Object.entries(explanation.by_group)
    .map(([name, value]) => ({ label: GROUP_LABELS[name] ?? humanise(name), value }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
  const features = explanation.by_feature.map((item) => ({
    label: featureLabel(String(item.feature)),
    value: Number(item.contribution),
  }));

  return (
    <section aria-label="Explanation">
      <ChartCard
        title="What moved this score"
        description="Contributions on the log-odds scale, starting from the model's base value. Red raises the score, blue lowers it. This shows how the model reacted to these inputs, not what causes fraud."
        tableColumns={[
          { key: "label", header: "Input group" },
          { key: "value", header: "Contribution (log-odds)", numeric: true },
          { key: "direction", header: "Effect" },
        ]}
        tableRows={groups.map((group) => ({
          label: group.label,
          value: group.value.toFixed(3),
          direction: group.value >= 0 ? "Raises the score" : "Lowers the score",
        }))}
      >
        <ContributionBars data={groups} />
      </ChartCard>
      <article className="card">
        <h2>By model input</h2>
        <p className="muted small">
          Base value {explanation.base_value.toFixed(3)} ({explanation.output_scale.replace("_", "-")}). Method:{" "}
          {explanation.method.replace(/_/g, " ")}.
        </p>
        <div className="table-wrap">
          <table className="data-table">
            <caption className="visually-hidden">Contribution of each model input</caption>
            <thead>
              <tr>
                <th scope="col">Model input</th>
                <th scope="col" className="numeric">
                  Contribution (log-odds)
                </th>
              </tr>
            </thead>
            <tbody>
              {features.map((feature) => (
                <tr key={feature.label}>
                  <td>{feature.label}</td>
                  <td className="numeric">{feature.value.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h3>Limits of this explanation</h3>
        <ul className="small">
          {explanation.limitations.map((limit) => (
            <li key={limit}>{limit}</li>
          ))}
        </ul>
      </article>
    </section>
  );
}
