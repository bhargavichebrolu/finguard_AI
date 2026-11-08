/**
 * Realistic API responses for component tests, typed against the generated API schema so a
 * change to the API breaks the build here rather than slipping through.
 *
 * Figures in these fixtures are test inputs only. The application never contains them.
 */
import type {
  CurrentUser,
  FeatureImportance,
  ModelMetrics,
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
