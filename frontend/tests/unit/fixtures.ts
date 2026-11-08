/**
 * Realistic API responses for component tests, typed against the generated API schema so a
 * change to the API breaks the build here rather than slipping through.
 *
 * Figures in these fixtures are test inputs only. The application never contains them.
 */
import type { CurrentUser, ModelMetrics, SystemStatus } from "../../src/services/endpoints";

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
