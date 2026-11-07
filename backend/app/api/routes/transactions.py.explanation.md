# transactions.py (routes)

Source: [backend/app/api/routes/transactions.py](transactions.py)

## A. File Purpose
Exposes scoring of one transaction, the searchable explorer and the detail view.

## B. Why This File Exists
These are the PRD 8.2 transaction endpoints, implementing PRD 6.2, 6.5 and 6.6.

## C. Dependencies
- **Libraries:** `fastapi`.
- **Internal modules:** `app.api.schemas`, `app.repositories.transactions`, `app.security`, `app.services.prediction_service`, `app.core`, `app.models`.
- **External services / database:** through the service and repository.
- **Depended on by:** `app/api/router.py`.

## D. Every Function Explained

### `predict`
- **Purpose:** `POST /api/v1/transactions/predict`.
- **Parameters / types:** `user`, `db`, `model`, `body: TransactionInput`. **Returns / type:** `PredictionView`, status 201.
- **Internal processing:** calls the service.
- **Error handling:** 422 for invalid input, 409 for a repeated identifier, 429 when limited.
- **Calls:** `create_prediction`. **Used by:** clients.

### `explore`
- **Purpose:** `GET /api/v1/transactions`.
- **Parameters / types:** each PRD 6.5 filter, plus sorting and paging. **Returns / type:** `Page[TransactionSummary]`.
- **Internal processing:** builds `TransactionFilters`, and separates demo records by role.
- **Error handling:** invalid filter values give 422.
- **Calls:** `list_transactions`, `transaction_summary`. **Used by:** clients.

### `read_transaction`
- **Purpose:** `GET /api/v1/transactions/{transaction_id}`.
- **Parameters / types:** `user`, `db`, `transaction_id`. **Returns / type:** `TransactionDetail`.
- **Internal processing:** loads the row, with notes and history.
- **Error handling:** 404 if missing or in the other demo scope.
- **Calls:** `get_transaction`, `transaction_detail`. **Used by:** clients.

## E. Classes Explained
None. `PredictUser` and `ViewUser` are type aliases carrying the permission and limit checks.

## F. Execution Flow
Permission and rate limit, validation, service or repository, then the response schema.

## G. Input and Output
See `API_DOCUMENTATION.md` for full examples.

## H. Important Technical Concepts
- **Docstrings appear in `/docs`,** which is why `predict` repeats the score warning.
- **Sync routes:** FastAPI runs them on a thread pool, so model work does not block other requests.

## I. Example
```powershell
curl.exe -H "Authorization: Bearer <token>" "http://127.0.0.1:8010/api/v1/transactions?risk_level=HIGH&sort_by=model_score"
```

## J. Maintenance Notes
Keep logic in services and repositories.

## K. Related Files
- [prediction_service.py](../../services/prediction_service.py.explanation.md): scoring and storage.
- [transactions.py repository](../../repositories/transactions.py.explanation.md): queries.
- [test_transactions.py](../../../tests/api/test_transactions.py.explanation.md): tests.
