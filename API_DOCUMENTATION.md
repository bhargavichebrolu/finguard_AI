# API Documentation

**Status: planned for Phase 3. No API exists yet.** The endpoint list below is the contract from PRD section 8.2. Once built, FastAPI will also serve interactive documentation at `/docs`, and this file will describe schemas, authentication and errors.

| Area | Method and path |
|---|---|
| Health | `GET /health`, `GET /api/v1/system/status` |
| Transactions | `POST /api/v1/transactions/predict`, `GET /api/v1/transactions`, `GET /api/v1/transactions/{transaction_id}` |
| Batches | `POST /api/v1/batches/upload`, `GET /api/v1/batches/{batch_id}`, `GET /api/v1/batches/{batch_id}/results`, `GET /api/v1/batches/{batch_id}/export` |
| Investigations | `GET /api/v1/investigations`, `PATCH /api/v1/investigations/{investigation_id}`, `POST /api/v1/investigations/{investigation_id}/notes` |
| Models | `GET /api/v1/models`, `GET /api/v1/models/active`, `GET /api/v1/models/metrics`, `GET /api/v1/models/feature-importance` |
| Reports | `GET /api/v1/reports/summary`, `GET /api/v1/reports/export` |
| Settings | `GET /api/v1/settings`, `PATCH /api/v1/settings` |

## Prediction input decided by Phase 1

The predict endpoint accepts exactly the four values below, which match `PREDICTION_INPUT_COLUMNS` in `backend/app/ml/schema.py`. It must never ask for post-transaction balances.

| Field | Type | Notes |
|---|---|---|
| `amount` | number | Proposed: must be greater than 0 |
| `transaction_type` | enum | CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER |
| `step` | integer | Simulation step |
| `destination_category` | enum | customer, merchant |

Proposed for Phase 3: reject type and destination combinations that never occur in the training data (merchant is valid only with PAYMENT), rather than returning a score the model has no basis for. See [ADR 0001](docs/decisions/0001-phase-1-decisions.md).
