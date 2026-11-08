/**
 * How values are written on screen.
 *
 * model_score is shown as a plain number and never with a percent sign, because it is not a
 * probability. Rates measured in Phase 2, such as recall, are genuine proportions and may be
 * written as percentages.
 */

const SCORE_DECIMALS = 4;
const amountFormatter = new Intl.NumberFormat("en-GB", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const countFormatter = new Intl.NumberFormat("en-GB");

/** Write an uncalibrated model score, for example 0.8377. */
export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return "–";
  return score.toFixed(SCORE_DECIMALS);
}

/** Write the 0 to 100 risk score, making clear it is not a percentage. */
export function formatRiskScore(riskScore: number): string {
  return `${riskScore.toFixed(1)} (score × 100, not a percentage)`;
}

/** Write a measured proportion, such as recall, as a percentage. */
export function formatRate(rate: number | null | undefined, decimals = 1): string {
  if (rate === null || rate === undefined || Number.isNaN(rate)) return "–";
  return `${(rate * 100).toFixed(decimals)}%`;
}

/** Write a transaction amount in PaySim's currency units. */
export function formatAmount(amount: number): string {
  return amountFormatter.format(amount);
}

/** Write a whole count with thousands separators. */
export function formatCount(count: number): string {
  return countFormatter.format(count);
}

/** Write a timestamp in the reader's time zone. */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "–";
  return new Date(value).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
}

/** Turn an API value such as UNDER_REVIEW or cash_out into readable words. */
export function humanise(value: string): string {
  const words = value.toLowerCase().replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Describe the model's decision without claiming fraud. */
export function describeDecision(decision: string): string {
  return decision === "FLAG_FOR_REVIEW" ? "Flagged for review" : "Not flagged";
}
