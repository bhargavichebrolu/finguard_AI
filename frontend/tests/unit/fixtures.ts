/**
 * Realistic API responses for component tests, typed against the generated API schema so a
 * change to the API breaks the build here rather than slipping through.
 *
 * Figures in these fixtures are test inputs only. The application never contains them.
 */
import type {
  AppSettings,
  Batch,
  CurrentUser,
  FeatureImportance,
  ModelMetrics,
  ModelReport,
  Prediction,
  SummaryReport,
  SystemStatus,
  TransactionSummary,
} from "../../src/services/endpoints";

const EVERY_ROLE = [
  "predict",
  "upload_batch",
  "view_transactions",
  "view_models",
  "view_summary",
  "view_settings",
  "view_system_status",
];

export const PERMISSIONS: Record<string, string[]> = {
  demo: EVERY_ROLE,
  analyst: [...EVERY_ROLE, "view_investigations", "export_reports"],
  investigator: [...EVERY_ROLE, "view_investigations", "export_reports", "update_investigations"],
  admin: [
    ...EVERY_ROLE,
    "view_investigations",
    "export_reports",
    "update_investigations",
    "update_settings",
    "manage_users",
    "view_audit_log",
  ],
};

export function userFixture(role: keyof typeof PERMISSIONS = "analyst"): CurrentUser {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    email: `${role}@example.com`,
    role: role as CurrentUser["role"],
    is_active: true,
    created_at: "2026-11-08T09:00:00Z",
    permissions: [...PERMISSIONS[role]].sort(),
    session_expires_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
  };
}

export const TEST_NOTE_FPR = "Test note: false positive rate fixture sentence.";
export const TEST_NOTE_RECALL = "Test note: recall fixture sentence.";

export function metricsFixture(): ModelMetrics {
  const atThreshold = {
    accuracy: 0.9,
    alert_rate: 0.01,
    alerts: 10,
    balanced_accuracy: 0.7,
    f1: 0.3,
    false_negative_rate: 0.5,
    false_negatives: 5,
    false_positive_rate: 0.002,
    false_positives: 4,
    precision: 0.4,
    recall: 0.5,
    threshold: 0.03,
    true_negatives: 900,
    true_positives: 5,
  };
  const ranking = {
    brier: 0.01,
    fraud_rows: 10,
    pr_auc: 0.4,
    pr_auc_lift: 100,
    prevalence: 0.01,
    roc_auc: 0.95,
    rows: 1000,
  };
  return {
    model_version: "fraud_detector_v1",
    family: "xgboost",
    strategy: "original",
    feature_schema_version: "1.0.0",
    score_type: "uncalibrated_model_score",
    score_is_calibrated: false,
    score_semantics: "Not calibrated.",
    source: "fixture",
    threshold: { chosen_on: "validation", objective: "fixture", operational_fpr_cap: 0.001, value: 0.03 },
    validation: { at_threshold: atThreshold, ranking },
    test: {
      at_frozen_threshold: atThreshold,
      ranking,
      regimes: { normal: { at_frozen_threshold: atThreshold, ranking } },
    },
    performance_notes: [TEST_NOTE_FPR, TEST_NOTE_RECALL],
  };
}

export function statusFixture(): SystemStatus {
  return {
    status: "ok",
    application_version: "0.3.0",
    environment: "development",
    database_available: true,
    model_loaded: true,
    model_version: "fraud_detector_v1",
    model_sha256: "a".repeat(64),
    threshold: 0.03,
  };
}

export function predictionFixture(): Prediction {
  return {
    transaction_id: "33333333-3333-4333-8333-333333333333",
    external_transaction_id: "FIX-1",
    prediction_id: "44444444-4444-4444-8444-444444444444",
    amount: 9000000,
    transaction_type: "TRANSFER",
    step: 5,
    destination_category: "customer",
    model_score: 0.8377037048339844,
    score_type: "uncalibrated_model_score",
    score_is_calibrated: false,
    score_note: "Fixture note: scores rank transactions for review.",
    risk_score: 83.77037048339844,
    risk_level: "HIGH",
    prediction: "FLAG_FOR_REVIEW",
    model_version: "fraud_detector_v1",
    threshold_used: 0.03,
    high_risk_boundary_used: 0.3,
    is_demo: false,
    investigation_id: "55555555-5555-4555-8555-555555555555",
    investigation_status: "NEW",
    explanation: {
      method: "xgboost_tree_shap",
      output_scale: "log_odds",
      base_value: -6.5,
      by_group: { amount: 1.2, hour: 2.1, transaction_type_and_destination: 5.1 },
      by_feature: [
        { feature: "transaction_type_TRANSFER", contribution: 3.1 },
        { feature: "hour_of_day", contribution: -0.4 },
      ],
      limitations: ["SHAP explains this model's output. It does not establish that a feature causes fraud."],
    },
    created_at: "2026-11-08T10:00:00Z",
  };
}

export function summaryFixture(options: { empty?: boolean; demo?: boolean } = {}): SummaryReport {
  const empty = options.empty ?? false;
  const recent: TransactionSummary = {
    transaction_id: "33333333-3333-4333-8333-333333333333",
    external_transaction_id: "FIX-1",
    amount: 9000000,
    transaction_type: "TRANSFER",
    step: 5,
    destination_category: "customer",
    model_score: 0.8377,
    score_is_calibrated: false,
    risk_score: 83.77,
    risk_level: "HIGH",
    prediction: "FLAG_FOR_REVIEW",
    model_version: "fraud_detector_v1",
    threshold_used: 0.03,
    is_demo: options.demo ?? false,
    batch_job_id: null,
    investigation_id: null,
    investigation_status: "NEW",
    created_at: "2026-11-08T10:00:00Z",
  };
  return {
    scope: options.demo ? "demo_sample_records" : "application_records",
    is_demo: options.demo ?? false,
    note: "Fixture note: kept separate.",
    model_flags: {
      total_analysed: empty ? 0 : 20,
      flagged_for_review: empty ? 0 : 7,
      not_flagged: empty ? 0 : 13,
      flag_rate: empty ? 0 : 0.35,
      total_value: empty ? 0 : 1000,
      flagged_value: empty ? 0 : 600,
      risk_distribution: empty ? {} : { LOW: 13, MEDIUM: 4, HIGH: 3 },
      type_distribution: empty ? {} : { TRANSFER: { analysed: 10, flagged: 7 }, PAYMENT: { analysed: 10, flagged: 0 } },
      flags_by_simulation_day: empty ? [] : [{ day: 0, analysed: 20, flagged: 7 }],
    },
    investigation_workflow: { status_counts: empty ? {} : { NEW: 5, CLOSED: 2 } },
    uploaded_labels: { labelled_rows: empty ? 0 : 4, labelled_fraud_rows: empty ? 0 : 1, labelled_fraud_value: empty ? 0 : 50 },
    model_performance_notes: [TEST_NOTE_FPR],
    recent_activity: empty ? [] : [recent],
  };
}

export function featureImportanceFixture(): FeatureImportance {
  return {
    model_version: "fraud_detector_v1",
    output_scale: "log_odds",
    by_group: { amount: 0.5, hour: 0.3, transaction_type_and_destination: 2.1 },
    by_feature: { transaction_type_TRANSFER: 0.4, amount: 0.3 },
    limitations: ["Fixture limitation: does not show causes."],
  };
}

export function settingsFixture(): AppSettings {
  return {
    high_risk_boundary: 0.3,
    frozen_threshold: 0.03,
    frozen_threshold_is_editable: false,
    risk_bands: "Fixture bands: not calibrated.",
    application_version: "0.3.0",
    model_version: "fraud_detector_v1",
    database_available: true,
    max_upload_bytes: 1000,
    max_batch_rows: 50,
    dataset: {
      name: "PaySim (synthetic mobile money simulator)",
      source_file: "fixture.csv",
      preprocessing_version: "split-v1",
      feature_schema_version: "1.0.0",
      split_boundaries: { first_step: 1, last_step: 743 },
    },
  };
}

const FIXTURE_CURVES = {
  pr_precision: [1, 0.5, 0.1],
  pr_recall: [0, 0.4, 1],
  roc_fpr: [0, 0.2, 1],
  roc_tpr: [0, 0.7, 1],
};

function fixtureAt(threshold: number, precision: number, recall: number) {
  return {
    threshold,
    precision,
    recall,
    f1: 0.111,
    balanced_accuracy: 0.222,
    false_positive_rate: 0.000444,
    false_negative_rate: 1 - recall,
    alerts: 77,
    true_positives: 11,
    false_positives: 66,
    false_negatives: 22,
    true_negatives: 9900,
  };
}

function fixtureFamily(family: string, prAuc: number) {
  return {
    family,
    run_id: `${family}-fixture`,
    stage: "tuning",
    strategy: "class_weight",
    pr_auc: prAuc,
    pr_auc_mean_over_seeds: prAuc,
    pr_auc_seed_cv: 0,
    pr_auc_interval: { mean: prAuc, ci_low: prAuc - 0.05, ci_high: prAuc + 0.05 },
    difference_from_top: null,
    roc_auc: 0.876,
    at_fpr_cap: fixtureAt(0.0123, 0.345, 0.456),
    training_seconds: 12.5,
    batch_microseconds_per_row: 1.25,
    single_row_ms: 3.5,
  };
}

/** A small model report with the real shape and invented values. */
export function reportFixture(): ModelReport {
  return {
    report_version: "fixture",
    model_version: "fraud_detector_v1",
    threshold: 0.0123,
    source_files: { "artifacts/metrics/fixture.json": "abcdef0123456789abcdef" },
    notes: ["Fixture report note one.", "Fixture report note two."],
    selection: {
      decision: {
        selected_family: "xgboost",
        top_by_pr_auc: "catboost",
        statistically_indistinguishable: ["xgboost", "catboost"],
        tied_on_recall: ["xgboost"],
      },
    },
    families: [fixtureFamily("xgboost", 0.6111), fixtureFamily("catboost", 0.6222), fixtureFamily("decision_tree", 0.2333)],
    family_validation_curves: { xgboost: FIXTURE_CURVES, catboost: FIXTURE_CURVES, decision_tree: FIXTURE_CURVES },
    selected_model_curves: { validation: FIXTURE_CURVES, test: FIXTURE_CURVES },
    confusion_matrices: {
      validation: { true_positives: 101, false_positives: 202, false_negatives: 303, true_negatives: 40404 },
      test: { true_positives: 111, false_positives: 222, false_negatives: 333, true_negatives: 44444 },
      test_by_step_type: {},
    },
    thresholds: {
      selected_threshold: 0.0123,
      objective: "Fixture objective sentence.",
      selected: fixtureAt(0.0123, 0.345, 0.456),
      sweep: [fixtureAt(0.001, 0.1, 0.9), fixtureAt(0.01, 0.3, 0.5), fixtureAt(0.1, 0.8, 0.2)],
      prd_candidates: { "0.50": fixtureAt(0.5, 0.9, 0.1) },
      rule_alternatives: { "fpr_cap_0.005": fixtureAt(0.004, 0.2, 0.6), max_f1: fixtureAt(0.2, 0.7, 0.3) },
    },
    imbalance_matrix: [
      { family: "xgboost", strategy: "original", pr_auc: 0.5111, fpr_cap_recall: 0.3 },
      { family: "xgboost", strategy: "smote", pr_auc: 0.4111, fpr_cap_recall: 0.2 },
    ],
    experiment_history: [
      { run_id: "run-tuning-1", stage: "tuning", status: "ok", family: "xgboost", strategy: "original", seed: 42, pr_auc: 0.5555, roc_auc: 0.9, fpr_cap_precision: 0.2, fpr_cap_recall: 0.3, total_training_seconds: 10 },
      { run_id: "run-matrix-1", stage: "matrix", status: "ok", family: "catboost", strategy: "smote", seed: 7, pr_auc: 0.4444, roc_auc: 0.8, fpr_cap_precision: 0.1, fpr_cap_recall: 0.2, total_training_seconds: 20 },
    ],
    lightgbm_diagnostic: {},
  };
}

export function batchFixture(overrides: Partial<Batch> = {}): Batch {
  return {
    id: "66666666-6666-4666-8666-666666666666",
    filename: "upload.csv",
    status: "COMPLETED_WITH_ERRORS",
    total_records: 3,
    processed_records: 3,
    failed_records: 1,
    succeeded_records: 2,
    progress_percent: 100,
    ignored_columns: ["isFraud"],
    labels_supplied: true,
    is_demo: false,
    error_message: null,
    created_at: "2026-11-08T10:00:00Z",
    completed_at: "2026-11-08T10:00:05Z",
    ...overrides,
  };
}
