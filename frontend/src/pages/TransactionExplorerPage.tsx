/**
 * Transaction Explorer (PRD 6.5): search stored transactions with every PRD filter, sort, page,
 * and open one for the full detail view (PRD 6.6).
 */
import { useState, type FormEvent } from "react";

import { DecisionBadge, DemoBadge, RiskBadge, StatusBadge } from "../components/badges";
import { DataTable, Pager, type Column } from "../components/DataTable";
import { ErrorState, LoadingState, PageHeader } from "../components/feedback";
import { ScoreDisclosure } from "../components/ScoreDisclosure";
import { TransactionDetailPanel } from "../components/TransactionDetailPanel";
import { useApiResource } from "../hooks/useApiResource";
import { transactionsApi, type TransactionQuery, type TransactionSummary } from "../services/endpoints";
import { formatAmount, formatDateTime, formatScore, humanise } from "../utils/format";

const PAGE_SIZE = 25;

export interface ExplorerFilters {
  externalId: string;
  riskLevel: string;
  prediction: string;
  transactionType: string;
  amountMin: string;
  amountMax: string;
  stepMin: string;
  stepMax: string;
  investigationStatus: string;
  sortBy: "created_at" | "amount" | "model_score" | "step";
  sortOrder: "asc" | "desc";
}

export const EMPTY_FILTERS: ExplorerFilters = {
  externalId: "",
  riskLevel: "",
  prediction: "",
  transactionType: "",
  amountMin: "",
  amountMax: "",
  stepMin: "",
  stepMax: "",
  investigationStatus: "",
  sortBy: "created_at",
  sortOrder: "desc",
};

/** Turn the form into API query parameters, leaving out anything blank. */
export function toQuery(filters: ExplorerFilters, offset: number): TransactionQuery {
  const query: Record<string, string | number> = {
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
    limit: PAGE_SIZE,
    offset,
  };
  const optional: [string, string][] = [
    ["external_id", filters.externalId.trim()],
    ["risk_level", filters.riskLevel],
    ["prediction", filters.prediction],
    ["transaction_type", filters.transactionType],
    ["amount_min", filters.amountMin],
    ["amount_max", filters.amountMax],
    ["step_min", filters.stepMin],
    ["step_max", filters.stepMax],
    ["investigation_status", filters.investigationStatus],
  ];
  for (const [key, value] of optional) {
    if (value !== "") query[key] = value;
  }
  return query as TransactionQuery;
}

const COLUMNS: Column<TransactionSummary>[] = [
  {
    key: "id",
    header: "Transaction",
    render: (row) => (
      <>
        {row.external_transaction_id} {row.is_demo ? <DemoBadge /> : null}
      </>
    ),
  },
  { key: "type", header: "Type", render: (row) => humanise(row.transaction_type) },
  { key: "amount", header: "Amount", render: (row) => formatAmount(row.amount), numeric: true },
  { key: "step", header: "Step", render: (row) => row.step, numeric: true },
  { key: "score", header: "Model score", render: (row) => formatScore(row.model_score), numeric: true },
  { key: "risk", header: "Risk", render: (row) => <RiskBadge level={row.risk_level} /> },
  { key: "decision", header: "Decision", render: (row) => <DecisionBadge decision={row.prediction} /> },
  { key: "investigation", header: "Investigation", render: (row) => <StatusBadge status={row.investigation_status} /> },
  { key: "time", header: "Scored", render: (row) => formatDateTime(row.created_at) },
];

function Select({ id, label, value, options, onChange }: {
  id: string;
  label: string;
  value: string;
  options: [string, string][];
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </div>
  );
}

export function TransactionExplorerPage() {
  const [draft, setDraft] = useState<ExplorerFilters>(EMPTY_FILTERS);
  const [applied, setApplied] = useState<ExplorerFilters>(EMPTY_FILTERS);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const results = useApiResource(() => transactionsApi.list(toQuery(applied, offset)), [applied, offset]);
  const set = (key: keyof ExplorerFilters) => (value: string) => setDraft({ ...draft, [key]: value });

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setApplied(draft);
    setOffset(0);
  }

  function reset() {
    setDraft(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
    setOffset(0);
  }

  return (
    <section>
      <PageHeader title="Transaction Explorer">Search, filter and open stored predictions.</PageHeader>
      <ScoreDisclosure compact />
      <form className="card filters" onSubmit={apply} aria-label="Filters">
        <div className="filter-grid">
          <div>
            <label htmlFor="f-id">Transaction identifier contains</label>
            <input id="f-id" value={draft.externalId} onChange={(event) => set("externalId")(event.target.value)} />
          </div>
          <Select id="f-risk" label="Risk level" value={draft.riskLevel} onChange={set("riskLevel")}
            options={[["", "Any"], ["LOW", "Low"], ["MEDIUM", "Medium"], ["HIGH", "High"]]} />
          <Select id="f-decision" label="Decision" value={draft.prediction} onChange={set("prediction")}
            options={[["", "Any"], ["FLAG_FOR_REVIEW", "Flagged for review"], ["NOT_FLAGGED", "Not flagged"]]} />
          <Select id="f-type" label="Transaction type" value={draft.transactionType} onChange={set("transactionType")}
            options={[["", "Any"], ...["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"].map((t): [string, string] => [t, t])]} />
          <div>
            <label htmlFor="f-amount-min">Amount from</label>
            <input id="f-amount-min" inputMode="decimal" value={draft.amountMin} onChange={(event) => set("amountMin")(event.target.value)} />
          </div>
          <div>
            <label htmlFor="f-amount-max">Amount to</label>
            <input id="f-amount-max" inputMode="decimal" value={draft.amountMax} onChange={(event) => set("amountMax")(event.target.value)} />
          </div>
          <div>
            <label htmlFor="f-step-min">Step from</label>
            <input id="f-step-min" inputMode="numeric" value={draft.stepMin} onChange={(event) => set("stepMin")(event.target.value)} />
          </div>
          <div>
            <label htmlFor="f-step-max">Step to</label>
            <input id="f-step-max" inputMode="numeric" value={draft.stepMax} onChange={(event) => set("stepMax")(event.target.value)} />
          </div>
          <Select id="f-status" label="Investigation status" value={draft.investigationStatus} onChange={set("investigationStatus")}
            options={[["", "Any"], ...["NEW", "UNDER_REVIEW", "ESCALATED", "CLOSED", "FALSE_ALARM"].map((s): [string, string] => [s, humanise(s)])]} />
          <Select id="f-sort" label="Sort by" value={draft.sortBy} onChange={set("sortBy")}
            options={[["created_at", "Time scored"], ["model_score", "Model score"], ["amount", "Amount"], ["step", "Step"]]} />
          <Select id="f-order" label="Order" value={draft.sortOrder} onChange={set("sortOrder")}
            options={[["desc", "Highest or newest first"], ["asc", "Lowest or oldest first"]]} />
        </div>
        <div className="button-row">
          <button type="submit" className="button primary">Apply filters</button>
          <button type="button" className="button secondary" onClick={reset}>Reset</button>
        </div>
      </form>
      <article className="card">
        {results.loading ? <LoadingState /> : null}
        {results.error ? <ErrorState error={results.error} onRetry={results.reload} /> : null}
        {results.data ? (
          <>
            <DataTable
              caption="Stored transactions"
              columns={COLUMNS}
              rows={results.data.items}
              rowKey={(row) => row.transaction_id}
              emptyTitle="No transactions match"
              emptyMessage="Change or reset the filters."
              onRowSelect={(row) => setSelected(row.transaction_id)}
              selectedKey={selected}
            />
            <Pager total={results.data.total} limit={PAGE_SIZE} offset={offset} onChange={setOffset} />
          </>
        ) : null}
      </article>
      {selected ? <TransactionDetailPanel transactionId={selected} onClose={() => setSelected(null)} /> : null}
    </section>
  );
}
