/**
 * Typed views of the model report's sections.
 *
 * The API declares these sections as general JSON, because the report is copied unchanged from
 * saved Phase 2 files. These interfaces describe the fields the Model Performance page reads.
 * `test_model_report.py` in the backend checks the values against their sources.
 */
import type { ModelReport } from "../services/endpoints";

export interface Curves {
  pr_precision: number[];
  pr_recall: number[];
  roc_fpr: number[];
  roc_tpr: number[];
}

export interface AtThreshold {
  threshold: number;
  precision: number;
  recall: number;
  f1: number;
  balanced_accuracy: number;
  false_positive_rate: number;
  false_negative_rate: number;
  alerts: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  true_negatives: number;
}

export interface Interval {
  mean: number;
  ci_low: number;
  ci_high: number;
  includes_zero?: boolean;
}

export interface FamilyRow {
  family: string;
  run_id: string;
  strategy: string;
  pr_auc: number;
  pr_auc_mean_over_seeds: number;
  pr_auc_interval: Interval;
  difference_from_top: Interval | null;
  roc_auc: number;
  at_fpr_cap: AtThreshold;
  training_seconds: number;
  batch_microseconds_per_row: number;
  single_row_ms: number;
}

export interface HistoryRow {
  run_id: string;
  stage: string;
  status: string;
  family: string;
  strategy: string;
  seed: number | null;
  pr_auc: number | null;
  roc_auc: number | null;
  fpr_cap_precision: number | null;
  fpr_cap_recall: number | null;
  total_training_seconds: number | null;
}

export interface MatrixCell {
  family: string;
  strategy: string;
  pr_auc: number;
  fpr_cap_recall: number;
}

export interface Confusion {
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  true_negatives: number;
}

export interface Decision {
  selected_family: string;
  top_by_pr_auc: string;
  statistically_indistinguishable: string[];
  tied_on_recall: string[];
}

export interface TypedReport {
  notes: string[];
  decision: Decision;
  families: FamilyRow[];
  familyCurves: Record<string, Curves>;
  selectedCurves: { validation: Curves; test: Curves };
  confusion: { validation: Confusion; test: Confusion; test_by_step_type: Record<string, Confusion> };
  thresholds: {
    selected_threshold: number;
    objective: string;
    selected: AtThreshold;
    sweep: AtThreshold[];
    prd_candidates: Record<string, AtThreshold>;
    rule_alternatives: Record<string, AtThreshold>;
  };
  matrix: MatrixCell[];
  history: HistoryRow[];
}

/** Read the report's sections under the field names the page uses. */
export function readReport(report: ModelReport): TypedReport {
  return {
    notes: report.notes,
    decision: report.selection.decision as Decision,
    families: report.families as unknown as FamilyRow[],
    familyCurves: report.family_validation_curves as unknown as Record<string, Curves>,
    selectedCurves: report.selected_model_curves as unknown as TypedReport["selectedCurves"],
    confusion: report.confusion_matrices as unknown as TypedReport["confusion"],
    thresholds: report.thresholds as unknown as TypedReport["thresholds"],
    matrix: report.imbalance_matrix as unknown as MatrixCell[],
    history: report.experiment_history as unknown as HistoryRow[],
  };
}

/** Pair two equal-length arrays into chart points. */
export function toPoints(xs: number[], ys: number[]): { x: number; y: number }[] {
  return xs.map((x, index) => ({ x, y: ys[index] }));
}
