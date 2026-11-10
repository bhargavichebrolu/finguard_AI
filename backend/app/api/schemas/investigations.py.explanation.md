# investigations.py (schemas)

Source: [backend/app/api/schemas/investigations.py](investigations.py)

## A. File Purpose
Defines the investigation list row, the update request and the new-note request.

## B. Why This File Exists
PRD 6.7 describes the workflow, and PRD 8.2 requires schemas. PRD 6.7 also states that these are workflow labels and not verified findings, so every row carries that statement.

## C. Dependencies
- **Libraries:** `pydantic`.
- **Internal modules:** `app.api.schemas.common`, `app.models.enums`.
- **External services / database:** none.
- **Depended on by:** the investigations route and service.

## D. Every Function Explained

### `_must_change_something`
- **Purpose:** refuse an empty update or a null status.
- **Parameters / types:** the update object. **Returns / type:** `InvestigationUpdate`.
- **Internal processing:** `model_fields_set` shows which fields the client actually sent, which is what separates "unassign" (`null`) from "leave as it is" (absent).
- **Error handling:** raises `ValueError`, which becomes a 422.
- **Calls:** none. **Used by:** pydantic.

## E. Classes Explained

### `InvestigationSummary`
A list row with the transaction and score. `status_note` carries the workflow statement. **Inheritance:** `ApiModel`.

### `InvestigationUpdate`
Optional `status` and `assigned_user_id`. **Inheritance:** `BaseModel`.

### `NoteCreate`
`note`, trimmed, 1 to 5,000 characters. **Inheritance:** `BaseModel`.

## F. Execution Flow
FastAPI validates requests against these before the route runs.

## G. Input and Output
`{"status": "UNDER_REVIEW"}` changes the status. `{"assigned_user_id": null}` unassigns.

## H. Important Technical Concepts
- **`expected_status` (Phase 5 M7):** optional; the status the caller last saw. `_must_change_something` now requires `status` or `assigned_user_id`, so `expected_status` alone is refused.
- **Three truths stay separate (PRD 6.1).** `prediction` is the model's output, and `status` is a person's workflow label. A list row shows both, under different names, and neither changes the other.

## I. Example
```json
{"note": "Amount matches a known test pattern. Asked for more detail."}
```

## J. Maintenance Notes
Do not add a "confirmed fraud" status. PRD 6.7 fixes the list.

## K. Related Files
- [investigation_service.py](../../services/investigation_service.py.explanation.md): the rules.
- [transactions.py schemas](transactions.py.explanation.md): the detail view.
