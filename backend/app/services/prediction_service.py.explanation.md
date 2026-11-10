# prediction_service.py

Source: [backend/app/services/prediction_service.py](prediction_service.py)

## A. File Purpose
Scores validated transactions, and stores the transaction, its prediction and any new investigation together.

## B. Why This File Exists
PRD 6.2 lists the prediction steps, and PRD 9.2 requires related updates to share a database transaction. Single and batch predictions both use this code, which keeps them identical.

## C. Dependencies
- **Libraries:** `pandas`, `sqlalchemy`.
- **Internal modules:** `app.api.schemas.transactions`, `app.core`, `app.models`, `app.services.audit_service`, `app.services.model_service`, `app.services.risk`, `app.services.settings_service`.
- **External services / database:** `transactions`, `predictions`, `investigations`, `investigation_status_history`, `audit_logs`.
- **Depended on by:** the transactions route and `batch_service.py`.

## D. Every Function Explained

### `inputs_frame`
- **Purpose:** build the model's input table.
- **Parameters / types:** `payloads`. **Returns / type:** `pd.DataFrame`.
- **Internal processing:** takes exactly the four input fields.
- **Error handling:** none needed. **Calls:** `pandas`. **Used by:** `score_inputs`.

### `score_inputs`
- **Purpose:** score rows and classify them.
- **Parameters / types:** `model`, `payloads`, `high_boundary: float`, `explain_all: bool`. **Returns / type:** `list[ScoredInput]`.
- **Internal processing:** scores all rows together, classifies each, then explains all of them or only flagged ones.
- **Error handling:** an empty list returns an empty list.
- **Calls:** `inputs_frame`, `model.score`, `assess_score`, `model.explain`. **Used by:** `create_prediction`, `batch_service`.

### `new_external_id`
Returns `TXN-` plus a random hexadecimal value, for a transaction submitted without an identifier.

### `add_prediction_records`
- **Purpose:** add the prediction, and an investigation for a flagged row.
- **Parameters / types:** `session`, `transaction_id`, `scored`, `model`, `high_boundary`, `is_demo`. **Returns / type:** `tuple[Prediction, Investigation | None]`.
- **Internal processing:** records the model version, threshold and boundary used. It opens an investigation with a first history entry, except for demo records. It does not commit, so the caller controls the transaction.
- **Error handling:** database constraints refuse contradictions when flushed.
- **Calls:** `session.add`. **Used by:** `create_prediction`, `batch_service`.

### `create_prediction`
- **Purpose:** handle one prediction request.
- **Parameters / types:** `session`, `model`, `payload`, `user`. **Returns / type:** `PredictionView`.
- **Internal processing:** reads the boundary, scores first, then stores. It refreshes the prediction to get the database's timestamp.
- **Error handling:** a repeated identifier raises `ConflictError`. Any failure before `commit` stores nothing.
- **Calls:** `score_inputs`, `add_prediction_records`, `record_event`, `prediction_view`. **Used by:** the transactions route.

## E. Classes Explained

### `ScoredInput`
- **Purpose:** one scored row. **Attributes:** `payload`, `score`, `assessment`, `explanation`. **Methods:** none. **Inheritance:** none; a frozen dataclass.

## F. Execution Flow
Validate (schema), build the table, score, classify, explain, store, commit, respond.

## G. Input and Output
Input: a `TransactionInput`. Output: a `PredictionView`, and rows in the tables above.

## H. Important Technical Concepts
- **Scoring failures (Phase 5 M7):** `create_prediction` scores before writing anything; if the model raises, it logs the trace and raises `ScoringError`, so nothing is stored and the user gets a reference to quote.
- **Labels cannot reach the model:** `inputs_frame` names its four fields, and `ScoredInput` carries no label.
- **`float(payload.amount)`:** the same conversion the data pipeline used for amounts.
- **Investigations mean review, not guilt.** A `NEW` investigation means a person should look at it. With a test precision of 40.7%, most of those opened will not be labelled fraud.
- **Demo records** get scores and explanations but no investigation, keeping the real review queue clean.

## I. Example
```python
create_prediction(
    session,
    model,
    TransactionInput(
        amount="181.00", transaction_type="TRANSFER", step=2, destination_category="customer"
    ),
    user,
)
```

## J. Maintenance Notes
Do not add inputs to `inputs_frame` without a new model. Keep the order of scoring before storing, so a failure in the model stores nothing.

## K. Related Files
- [model_service.py](model_service.py.explanation.md): scoring.
- [risk.py](risk.py.explanation.md): classification.
- [transactions.py route](../api/routes/transactions.py.explanation.md): the entry point.
