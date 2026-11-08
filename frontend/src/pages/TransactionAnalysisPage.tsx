/**
 * Transaction Analysis (PRD 6.2): score one transaction with the frozen model and show the
 * result and its explanation. Only the four prediction inputs are asked for.
 */
import { useState, type FormEvent } from "react";

import { ExplanationPanel } from "../components/ExplanationPanel";
import { ErrorState, PageHeader } from "../components/feedback";
import { PredictionResult } from "../components/PredictionResult";
import { ScoreDisclosure } from "../components/ScoreDisclosure";
import { ApiError, toApiError } from "../services/api";
import { transactionsApi, type Prediction, type TransactionInput } from "../services/endpoints";

const TYPES = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"] as const;
const AMOUNT_PATTERN = /^\d+(\.\d{1,2})?$/;
const ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$/;

interface FormState {
  externalId: string;
  amount: string;
  type: (typeof TYPES)[number];
  step: string;
}

type FieldErrors = Partial<Record<"externalId" | "amount" | "step", string>>;

/** Check the form before sending. The API checks everything again. */
export function validateForm(form: FormState): FieldErrors {
  const errors: FieldErrors = {};
  if (!AMOUNT_PATTERN.test(form.amount) || Number(form.amount) <= 0) {
    errors.amount = "Enter an amount above 0 with at most two decimal places.";
  }
  if (!/^\d+$/.test(form.step) || Number(form.step) < 1 || Number(form.step) > 1_000_000) {
    errors.step = "Enter a whole step from 1 to 1,000,000.";
  }
  if (form.externalId && !ID_PATTERN.test(form.externalId)) {
    errors.externalId = "Use up to 64 letters, digits, dots, colons, dashes or underscores, starting with a letter or digit.";
  }
  return errors;
}

/** In PaySim a merchant receives only PAYMENT, so the destination follows from the type. */
export function destinationFor(type: string): "merchant" | "customer" {
  return type === "PAYMENT" ? "merchant" : "customer";
}

export function TransactionAnalysisPage() {
  const [form, setForm] = useState<FormState>({ externalId: "", amount: "", type: "TRANSFER", step: "" });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors = validateForm(form);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    const input: TransactionInput = {
      amount: form.amount,
      transaction_type: form.type,
      step: Number(form.step),
      destination_category: destinationFor(form.type),
      ...(form.externalId ? { external_transaction_id: form.externalId } : {}),
    };
    setBusy(true);
    setError(null);
    try {
      setResult(await transactionsApi.predict(input));
    } catch (caught) {
      setResult(null);
      setError(toApiError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <PageHeader title="Transaction Analysis">
        Score one simulated transaction with the frozen model. Post-transaction balances are not
        asked for, because they are not known when a transaction is assessed.
      </PageHeader>
      <ScoreDisclosure compact />
      <div className="grid two analysis-grid">
        <form className="card" onSubmit={(event) => void handleSubmit(event)} noValidate aria-label="Transaction details">
          <h2>Transaction</h2>
          <label htmlFor="amount">Amount</label>
          <input
            id="amount"
            inputMode="decimal"
            value={form.amount}
            onChange={(event) => setForm({ ...form, amount: event.target.value })}
            aria-invalid={Boolean(fieldErrors.amount)}
            aria-describedby={fieldErrors.amount ? "amount-error" : undefined}
          />
          {fieldErrors.amount ? <p id="amount-error" className="error-text">{fieldErrors.amount}</p> : null}

          <label htmlFor="type">Transaction type</label>
          <select id="type" value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value as FormState["type"] })}>
            {TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>

          <label htmlFor="destination">Destination category</label>
          <select id="destination" value={destinationFor(form.type)} disabled aria-describedby="destination-hint">
            <option value="customer">customer</option>
            <option value="merchant">merchant</option>
          </select>
          <p id="destination-hint" className="hint">
            Set by the type: in PaySim, merchants receive only PAYMENT, so the model has never seen any other combination.
          </p>

          <label htmlFor="step">Simulation step</label>
          <input
            id="step"
            inputMode="numeric"
            value={form.step}
            onChange={(event) => setForm({ ...form, step: event.target.value })}
            aria-invalid={Boolean(fieldErrors.step)}
            aria-describedby="step-hint"
          />
          <p id="step-hint" className="hint">
            One step is one simulated hour. The model uses only the hour of day.
          </p>
          {fieldErrors.step ? <p className="error-text">{fieldErrors.step}</p> : null}

          <label htmlFor="external-id">Transaction identifier (optional)</label>
          <input
            id="external-id"
            value={form.externalId}
            onChange={(event) => setForm({ ...form, externalId: event.target.value })}
            aria-invalid={Boolean(fieldErrors.externalId)}
          />
          {fieldErrors.externalId ? <p className="error-text">{fieldErrors.externalId}</p> : null}

          <button type="submit" className="button primary form-submit" disabled={busy}>
            {busy ? "Scoring…" : "Score transaction"}
          </button>
        </form>
        <div>
          {error ? <ErrorState error={error} /> : null}
          {result ? <PredictionResult prediction={result} /> : null}
          {!result && !error ? (
            <article className="card">
              <h2>Result</h2>
              <p className="muted">Enter a transaction and score it to see the result here.</p>
            </article>
          ) : null}
        </div>
      </div>
      {result ? <ExplanationPanel explanation={result.explanation} /> : null}
    </section>
  );
}
