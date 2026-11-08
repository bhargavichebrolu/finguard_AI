/**
 * Small labels for risk level, decision, workflow status and demo records.
 * Every badge carries text, so meaning never depends on colour alone.
 */
import { describeDecision, humanise } from "../utils/format";

const RISK_CLASS: Record<string, string> = { LOW: "badge-low", MEDIUM: "badge-medium", HIGH: "badge-high" };
const RISK_RULE: Record<string, string> = {
  LOW: "Below the frozen threshold: not flagged",
  MEDIUM: "At or above the threshold, below the high risk boundary: flagged for review",
  HIGH: "At or above the high risk boundary: flagged for review",
};

export function RiskBadge({ level }: { level: string }) {
  return (
    <span className={`badge ${RISK_CLASS[level] ?? ""}`} title={RISK_RULE[level]}>
      {humanise(level)} risk
    </span>
  );
}

export function DecisionBadge({ decision }: { decision: string }) {
  const flagged = decision === "FLAG_FOR_REVIEW";
  return <span className={`badge ${flagged ? "badge-flag" : "badge-neutral"}`}>{describeDecision(decision)}</span>;
}

export function StatusBadge({ status }: { status: string | null | undefined }) {
  if (!status) return <span className="muted">–</span>;
  return <span className="badge badge-status">{humanise(status)}</span>;
}

export function DemoBadge() {
  return <span className="badge badge-demo">Synthetic demo record</span>;
}
