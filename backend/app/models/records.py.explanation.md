# records.py

Source: [backend/app/models/records.py](records.py)

## A. File Purpose
Defines every database table as a SQLAlchemy class. This covers the PRD 9.1 tables, plus those needed for status history, row errors, labels and settings.

## B. Why This File Exists
PRD 9.2 requires SQLAlchemy models, enforced foreign keys and appropriate indexes. The tables reference each other heavily, so keeping them together makes those links easy to read and avoids circular imports.

## C. Dependencies
- **Libraries:** `sqlalchemy`, including PostgreSQL's `JSONB`.
- **Internal modules:** `app.database.base`, `app.models.enums`, `app.ml.schema`.
- **External services / database:** PostgreSQL.
- **Depended on by:** repositories, services, schemas, `migrations/env.py`.

## D. Every Function Explained
No functions: this file only declares tables.

## E. Classes Explained
All inherit from `Base`.

### `User`
`email` is unique, and services store it in lower case. `password_hash` holds an Argon2 hash. `token_version` goes up when a password changes, which invalidates older tokens.

### `UserSession`
One browser sign-in, added in Phase 4: user, CSRF token hash, expiry and revocation time. Logout sets `revoked_at` on this row only.

### `ModelVersion`
Filled from the frozen metadata at start-up. `uq_model_versions_single_active` is a partial unique index that allows only one active row.

### `BatchJob`
Tracks counts and status. `ignored_columns` lists uploaded columns that were dropped, and `labels_supplied` records whether a label column came with the file. The CSV is not stored in the database (PRD 9.2).

### `BatchRowError`
Row number, column and reason. The rejected value is deliberately left out, so a bad upload cannot put arbitrary content into the error report.

### `Transaction`
The four prediction inputs plus their origin. There are no balance or account identifier columns, so the leaky columns from PRD 4.3 cannot be stored. CHECK constraints repeat the input rules. `prediction` is a one-to-one relationship.

### `GroundTruthLabel`
A label from an upload, in a table of its own. No scoring code imports it.

### `Prediction`
- `model_version`, `threshold_used` and `high_risk_boundary_used` record what produced this row.
- `score_is_calibrated` must be false, enforced by `score_not_calibrated`.
- `decision_matches_threshold` makes it impossible to store a decision that contradicts the score and threshold.
- `low_risk_means_not_flagged` ties the risk band to the decision.
- `explanation_json` holds contributions by feature group where they were computed.

### `Investigation`
One per flagged prediction. `status` is a workflow label. `notes` and `history` are ordered relationships.

### `InvestigationNote`
The text and its author. `user_id` becomes null if the user is removed, keeping the note.

### `InvestigationStatusHistory`
Append-only record of status changes. `from_status` is null for the first entry. `changed_by` is null when the system created it.

### `AuditLog`
Who did what to which record. `details` must never hold a secret.

### `AppSetting`
Key and JSON value. Currently only the high risk boundary.

## F. Execution Flow
Imported at start-up, which registers the tables on `Base.metadata`. Alembic compares that metadata with the database.

## G. Input and Output
No runtime input. Output: table definitions and mapped classes.

## H. Important Technical Concepts
- **Rules are repeated in the database on purpose.** API validation gives clear messages, and CHECK constraints stop any other route from storing something invalid.
- **`Numeric(15, 2)` for amounts:** exact decimals, not binary fractions, so the stored amount is exactly what was scored.
- **`Float(53)` for scores:** double precision, so the comparison with the threshold gives the same result in the database as in Python.
- **`ondelete` choices:** child records of a transaction go with it (`CASCADE`), but removing a user keeps their work (`SET NULL`).

## I. Example
```python
session.get(Prediction, prediction_id).threshold_used  # 0.02841914258897305
```

## J. Maintenance Notes
Any change here needs an Alembic migration. `test_migrations.py` fails if the models and migrations disagree. Do not add balance fields to `Transaction`.

## K. Related Files
- [base.py](../database/base.py.explanation.md): helpers used here.
- [enums.py](enums.py.explanation.md): stored vocabularies.
- [DATABASE_SCHEMA.md](../../../DATABASE_SCHEMA.md): the schema described for readers.
