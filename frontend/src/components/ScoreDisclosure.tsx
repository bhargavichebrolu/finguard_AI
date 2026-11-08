/**
 * The statement shown beside every model score: what the score is, what a flag means, and how
 * the model performed. The performance sentences come from the API, so no figure is typed here.
 */
import { Info } from "lucide-react";

import { useModelLimits } from "../hooks/useModelLimits";

export const SCORE_MEANING =
  "Model scores rank transactions for human review. They are not calibrated and are not the " +
  "chance that a transaction is fraud. A flag asks a person to look; it is not a finding.";

export function ScoreDisclosure({ compact = false }: { compact?: boolean }) {
  const { notes, error, loading } = useModelLimits();
  const shown = compact ? notes.slice(0, 3) : notes;

  return (
    <aside className="disclosure" aria-label="How to read model scores">
      <Info className="disclosure-icon" aria-hidden="true" />
      <div>
        <p className="disclosure-lead">{SCORE_MEANING}</p>
        {loading ? <p className="muted small">Loading the model's measured limitations…</p> : null}
        {error ? (
          <p className="warning-text" role="alert">
            The model's measured limitations could not be loaded. Treat every score with extra
            caution until they are available.
          </p>
        ) : null}
        {shown.length > 0 ? (
          <ul className="disclosure-notes">
            {shown.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </aside>
  );
}
