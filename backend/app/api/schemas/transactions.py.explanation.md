# transactions.py

Source: [backend/app/api/schemas/transactions.py](transactions.py)

## A. File Purpose
Defines the prediction request, the prediction response, explorer rows and the transaction detail view.

## B. Why This File Exists
PRD 8.2 requires schemas, PRD 6.2 lists the allowed inputs, and PRD 6.6 lists the detail fields. The authorisation's wording rules are also enforced here: `model_score`, `score_is_calibrated: false`, and `FLAG_FOR_REVIEW`.

## C. Dependencies
- **Libraries:** `pydantic`, `decimal`.
- **Internal modules:** `app.api.schemas.common`, `app.core.frozen_model`, `app.ml.schema`, `app.models`, `app.services.model_service`.
- **External services / database:** none.
- **Depended on by:** transaction, batch and investigation routes, and `prediction_service.py`.

## D. Every Function Explained

### `_destination_must_fit_type`
- **Purpose:** enforce merchant if and only if PAYMENT.
- **Parameters / types:** the input object. **Returns / type:** `TransactionInput`.
- **Internal processing:** compares the two conditions.
- **Error handling:** raises `ValueError`, which becomes a 422.
- **Calls:** none. **Used by:** pydantic.

### `explanation_view`
Adds the standing limitations to a stored explanation, or returns `None`. Limitations are not stored per row, which saves space and keeps the wording current.

### `_shared_fields`
Maps the database columns shared by every view. Note that the API says `step`, and the column is `simulation_step`.

### `prediction_view`, `transaction_summary`, `transaction_detail`
Build the three response shapes from a transaction, its prediction and its investigation.

## E. Classes Explained

### `TransactionInput`
The input. `extra="forbid"` means sending `isFraud` or a balance gets a 422, so nobody can believe those fields influenced a score. `amount` allows two decimal places, so the stored value equals the scored value. **Inheritance:** `BaseModel`.

### `ExplanationView`
Base value and contributions on the log-odds scale, by feature and by group, plus limitations. **Inheritance:** `ApiModel`.

### `PredictionView`
The full response. `score_type`, `score_is_calibrated` and `score_note` are always present. `model_version` and `threshold_used` come from the stored row. **Inheritance:** `ApiModel`.

### `TransactionSummary`
A lighter row for lists, without explanations. **Inheritance:** `ApiModel`.

### `NoteView`, `StatusChangeView`
A note and a history entry. **Inheritance:** `ApiModel`.

### `InvestigationDetail`
Status, assignee, notes and history. Built from the ORM object with `from_attributes`. **Inheritance:** `ApiModel`.

### `TransactionDetail`
`PredictionView` plus the batch link and the investigation. **Inheritance:** `PredictionView`.

## F. Execution Flow
FastAPI validates the request against `TransactionInput`. After the service commits, a builder creates the response.

## G. Input and Output
Input:
```json
{"amount": 181.00, "transaction_type": "TRANSFER", "step": 2, "destination_category": "customer"}
```
Output includes `model_score`, `score_is_calibrated: false`, `risk_level`, `prediction`, `model_version` and `threshold_used`.

## H. Important Technical Concepts
- **`Decimal` input:** a binary float cannot represent most two-decimal amounts exactly.
- **`amount` goes out as a number.** This is for client convenience, and the database keeps the exact value.
- **`ExternalId` pattern:** must start with a letter or digit, which also rules out spreadsheet formula characters at the start of an exported cell.
- **The `step` value:** only its hour of day (`step % 24`) reaches the model, so a step beyond PaySim's 743 is accepted and treated by hour.

## I. Example
```python
TransactionInput(
    amount="10.00", transaction_type="PAYMENT", step=1, destination_category="merchant"
)
```

## J. Maintenance Notes
Never add a `probability` field. `test_transactions.py` checks that the word does not appear in responses or the OpenAPI schema.

## K. Related Files
- [prediction_service.py](../../services/prediction_service.py.explanation.md): uses these.
- [ADR 0003](../../../../docs/decisions/0003-phase-3-decisions.md): decisions 2, 3, 5 and 6.
