# Database Schema

**Status: planned for Phase 3. No database, model or migration exists yet.** This records the design from PRD section 9 so later work starts from it. Phase 3 will replace it with the implemented schema.

## Planned tables

| Table | Columns |
|---|---|
| `users` | id, email, password_hash, role, is_active, created_at |
| `transactions` | id, external_transaction_id, transaction_type, amount, simulation_step, destination_category, created_at |
| `predictions` | id, transaction_id, model_version, fraud_probability, risk_score, risk_level, prediction, threshold_used, created_at |
| `investigations` | id, prediction_id, status, assigned_user_id, created_at, updated_at |
| `investigation_notes` | id, investigation_id, user_id, note, created_at |
| `model_versions` | id, version, algorithm, model_path_or_artifact_reference, feature_schema_version, metrics_json, is_active, created_at |
| `batch_jobs` | id, filename, status, total_records, processed_records, failed_records, created_at, completed_at |
| `audit_logs` | id, user_id, action, entity_type, entity_id, created_at |

## Planned relationships

```
transactions 1---* predictions 1---* investigations 1---* investigation_notes
users 1---* investigations (assigned_user_id)
users 1---* investigation_notes
users 1---* audit_logs
```

## Points Phase 3 must resolve

The PRD's table list needs these additions to meet its other requirements:

| Requirement | Gap | Proposal |
|---|---|---|
| Status change history (PRD 6.7) | No table holds it | Add `investigation_status_history`, or define it through `audit_logs` |
| Batch results retrieval (PRD 8.2) | `transactions` has no batch link | Add a nullable `batch_job_id` |
| Keeping labels apart from predictions (PRD 6.1, 6.4) | No column holds an uploaded `isFraud` | Add a separate nullable ground-truth field, excluded from the prediction path |
| Configurable risk thresholds (PRD 6.3, 6.10) | No settings table | Add a settings table or a documented config source |

## Requirements carried forward

SQLAlchemy models, Alembic migrations, appropriate indexes, enforced foreign keys, transactions for related updates, no plaintext passwords, credentials outside source code, and no raw batch uploads as unbounded blobs.
