# Database Schema

**Status: implemented in Phase 3**, as SQLAlchemy models in `backend/app/models/records.py` and Alembic revisions `0001`, plus `0002` from Phase 4. PostgreSQL 17 runs locally in Docker. Nothing is deployed.

## Tables

The PRD 9.1 tables are marked PRD. The others close gaps the PRD's list left open, as planned before Phase 3.

| Table | Source | Columns |
|---|---|---|
| `users` | PRD | id, email (unique), password_hash (Argon2id), role, is_active, token_version, created_at |
| `transactions` | PRD | id, external_transaction_id (unique), transaction_type, amount `numeric(15,2)`, simulation_step, destination_category, is_demo, batch_job_id, created_by, created_at |
| `predictions` | PRD, renamed column | id, transaction_id (unique), model_version, **model_score**, score_is_calibrated, risk_score, risk_level, prediction, threshold_used, high_risk_boundary_used, explanation_json, created_at |
| `investigations` | PRD | id, prediction_id (unique), status, assigned_user_id, created_at, updated_at |
| `investigation_notes` | PRD | id, investigation_id, user_id, note, created_at |
| `model_versions` | PRD | id, version (unique), algorithm, model_path_or_artifact_reference, model_sha256, threshold, feature_schema_version, metrics_json, is_active, created_at |
| `batch_jobs` | PRD | id, filename, status, total_records, processed_records, failed_records, ignored_columns, labels_supplied, is_demo, error_message, created_by, created_at, completed_at; queue columns worker_id, lease_expires_at, attempts (Phase 5 M4, revision `0004`) |
| `batch_uploads` | added in Phase 5 M4 (revision `0004`) | job_id (primary key, cascades from batch_jobs), content: the checked upload's bytes, at most 10 MB, deleted when the job ends |
| `audit_logs` | PRD | id, user_id, action, entity_type, entity_id, details, created_at |
| `investigation_status_history` | added | id, investigation_id, from_status, to_status, changed_by, created_at |
| `batch_row_errors` | added | id, batch_job_id, row_number, column_name, message |
| `ground_truth_labels` | added | transaction_id (primary key), is_fraud, source, created_at |
| `app_settings` | added | key, value, updated_by, updated_at |
| `user_sessions` | added in Phase 4 (revision `0002`) | id, user_id, csrf_token_hash, created_at, expires_at, revoked_at |
| `rate_limit_events` | added in Phase 5 M3 (revision `0003`) | id, key, occurred_at (index on key and time): sliding-window events such as failed sign-ins |
| `rate_limit_windows` | added in Phase 5 M3 (revision `0003`) | key and window_start (primary key), count: fixed-window counters for predictions and uploads |

`predictions.fraud_probability` from PRD 9.1 is named `model_score`, as the Phase 3 authorisation requires, because the score is not calibrated. See [ADR 0003](docs/decisions/0003-phase-3-decisions.md).

## Relationships

```
users 1---* transactions (created_by)          batch_jobs 1---* transactions
transactions 1---1 predictions 1---0..1 investigations 1---* investigation_notes
                                                         1---* investigation_status_history
transactions 1---0..1 ground_truth_labels       model_versions 1---* predictions (by version)
users 1---* investigations (assigned_user_id), investigation_notes, audit_logs
batch_jobs 1---* batch_row_errors
batch_jobs 1---1 batch_uploads (only while the job is unfinished)
```

Deleting a transaction removes its prediction, investigation, notes, history and label (`CASCADE`). Deleting a user keeps their work and clears the reference (`SET NULL`). No route deletes either.

## Rules the database enforces

| Constraint | Rule |
|---|---|
| `ck_transactions_amount_positive` | `amount > 0` |
| `ck_transactions_step_positive` | `simulation_step >= 1` |
| `ck_transactions_known_type` | One of the five PaySim types |
| `ck_transactions_merchant_only_for_payment` | Merchant if and only if PAYMENT |
| `ck_predictions_score_in_range` | `model_score` between 0 and 1 |
| `ck_predictions_score_not_calibrated` | `score_is_calibrated` is false |
| `ck_predictions_decision_matches_threshold` | `FLAG_FOR_REVIEW` exactly when `model_score >= threshold_used` |
| `ck_predictions_low_risk_means_not_flagged` | `LOW` exactly when `NOT_FLAGGED` |
| `uq_model_versions_single_active` | At most one active model, through a partial unique index |
| Enum CHECK constraints | Roles, decisions, risk levels, statuses |
| Foreign keys | All relationships above |

These repeat the API's validation, so no other route into the database can store a contradiction. `test_migrations.py` checks each one by trying to break it.

## Indexes

On `transactions`: created_at, transaction_type, amount, simulation_step, is_demo and batch_job_id. On `predictions`: model_version, model_score, risk_level, prediction and created_at. On `investigations`: status and assigned_user_id. Plus status on `batch_jobs`, action, user and time on `audit_logs`, and the foreign keys of notes, history and row errors. Unique constraints index themselves.

## What is not stored

- No balance columns and no account identifiers. The PaySim columns that leak the label cannot be stored.
- No uploaded file. CSV files go to a temporary folder and are deleted after processing (PRD 9.2).
- No rejected values. Row errors record row, column and reason only.
- No passwords. Argon2id hashes only.
- No CSRF tokens. SHA-256 hashes only, in `user_sessions`.
- No note text, email address or password in the audit log.

## Roles and access

| Role | Rights | Used by |
|---|---|---|
| `POSTGRES_USER` (`finguard_admin`) | Superuser | Administration only |
| `APP_DB_USER` (`finguard_app`) | Owns `finguard`, `finguard_test` (backend suite) and `finguard_e2e_test` (browser tests, created by `scripts/e2e_stack.py`). No superuser, database or role creation rights. | API, migrations, tests |

Every authentication rule uses `scram-sha-256`, including connections inside the container, because `POSTGRES_INITDB_ARGS` is set from the first initialisation. Verified on 2026-11-07, both on a throwaway Compose project and on the development database:
- **Rules:** all 7 loaded rules in `pg_hba_file_rules` are SCRAM.
- **Wrong or missing passwords:** refused from Windows, from another container and inside the database container.
- **Persistence:** data survived removing and recreating the container on the same named volume, and authentication still worked afterwards.

## Migrations

```powershell
cd backend
uv run alembic upgrade head      # apply
uv run alembic check             # models and schema agree
uv run alembic downgrade base    # removes every table and all data
```

Inside Compose, the `migrate` service runs `alembic upgrade head` before the API starts. The API never changes the schema itself.
