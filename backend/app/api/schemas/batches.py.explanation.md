# batches.py (schemas)

Source: [backend/app/api/schemas/batches.py](batches.py)

## A. File Purpose
Defines what clients see about a batch job, including its progress.

## B. Why This File Exists
PRD 6.4 requires progress to be displayed, and PRD 8.2 requires response schemas.

## C. Dependencies
- **Libraries:** none beyond standard types.
- **Internal modules:** `app.api.schemas.common`, `app.models`.
- **External services / database:** none.
- **Depended on by:** the batches route.

## D. Every Function Explained

### `batch_view`
- **Purpose:** build the response from a job row.
- **Parameters / types:** `job: BatchJob`. **Returns / type:** `BatchView`.
- **Internal processing:** works out `succeeded_records` and `progress_percent`.
- **Error handling:** a total of zero gives 0% rather than dividing by zero.
- **Calls:** none. **Used by:** the batches route.

## E. Classes Explained

### `BatchView`
- **Purpose:** the response. **Attributes:** identifiers, status, counts, ignored columns, whether labels were supplied, timestamps. **Methods:** none. **Inheritance:** `ApiModel`.

## F. Execution Flow
A route loads a job, then calls `batch_view`.

## G. Input and Output
For example, `{"status": "COMPLETED_WITH_ERRORS", "total_records": 10, "processed_records": 10, "failed_records": 2, "succeeded_records": 8, "progress_percent": 100.0}`.

## H. Important Technical Concepts
- **`attempts`** (Phase 5 M4) counts how many times a worker claimed the job; above one while processing, the interface says it is resuming after an interruption.
- **`ignored_columns` tells the user what was dropped,** so the handling of `isFraud` is visible rather than silent.

## I. Example
```python
batch_view(job).progress_percent
```

## J. Maintenance Notes
Keep worked-out values here rather than storing them.

## K. Related Files
- [batch_service.py](../../services/batch_service.py.explanation.md): updates the counts.
- [batches.py route](../routes/batches.py.explanation.md): uses this schema.
