/**
 * The outcome of scoring one transaction: decision, risk band, uncalibrated score and the
 * settings that produced it.
 */
import type { Prediction } from "../services/endpoints";
import { formatAmount, formatDateTime, formatRiskScore, formatScore, humanise } from "../utils/format";
import { DecisionBadge, DemoBadge, RiskBadge, StatusBadge } from "./badges";

export function PredictionResult({ prediction }: { prediction: Prediction }) {
  return (
    <article className="card result-card" aria-label="Prediction result">
      <div className="result-header">
        <h2>Result</h2>
        <DecisionBadge decision={prediction.prediction} />
        <RiskBadge level={prediction.risk_level} />
        {prediction.is_demo ? <DemoBadge /> : null}
      </div>
      <dl className="facts">
        <dt>Model score (uncalibrated)</dt>
        <dd className="score">{formatScore(prediction.model_score)}</dd>
        <dt>Risk score</dt>
        <dd>{formatRiskScore(prediction.risk_score)}</dd>
        <dt>Review threshold used</dt>
        <dd>{formatScore(prediction.threshold_used)}</dd>
        <dt>High risk boundary used</dt>
        <dd>{formatScore(prediction.high_risk_boundary_used)}</dd>
        <dt>Model version</dt>
        <dd>{prediction.model_version}</dd>
        <dt>Transaction</dt>
        <dd>
          {prediction.external_transaction_id}: {humanise(prediction.transaction_type)},{" "}
          {formatAmount(prediction.amount)}, step {prediction.step}, to a {prediction.destination_category}
        </dd>
        <dt>Investigation</dt>
        <dd>
          <StatusBadge status={prediction.investigation_status} />
          {prediction.investigation_status ? null : (
            <span className="muted"> None opened{prediction.is_demo ? " for demo records" : ""}</span>
          )}
        </dd>
        <dt>Scored</dt>
        <dd>{formatDateTime(prediction.created_at)}</dd>
      </dl>
      <p className="muted small">{prediction.score_note}</p>
    </article>
  );
}
