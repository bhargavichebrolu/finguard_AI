# enums.py

Source: [backend/app/models/enums.py](enums.py)

## A. File Purpose
Defines the fixed lists of values for roles, decisions, risk levels, investigation statuses and batch statuses.

## B. Why This File Exists
These words carry meaning for users and auditors. Defining them once keeps the database, API and documents consistent, and each docstring records what a word does not mean.

## C. Dependencies
- **Libraries:** `enum`.
- **Internal modules:** none.
- **External services / database:** none directly. Values are stored by `enum_type`.
- **Depended on by:** models, schemas, services and permissions.

## D. Every Function Explained
No functions.

## E. Classes Explained

### `UserRole`
`admin`, `investigator`, `analyst` and `demo`, matching the user types in PRD section 2.

### `PredictionDecision`
`FLAG_FOR_REVIEW` when the score is at or above the frozen threshold, otherwise `NOT_FLAGGED`. The authorisation requires this wording rather than a claim of confirmed fraud.

### `RiskLevel`
`LOW`, `MEDIUM` and `HIGH`, from PRD 6.3. Low is exactly the same set as not flagged.

### `InvestigationStatus`
`NEW`, `UNDER_REVIEW`, `ESCALATED`, `CLOSED` and `FALSE_ALARM`, from PRD 6.7.

### `BatchStatus`
`PENDING` and `PROCESSING` are in progress. `COMPLETED` had no row errors, `COMPLETED_WITH_ERRORS` had some, and `FAILED` means the job stopped.

**Inheritance:** all inherit from `enum.StrEnum`, so each member behaves as its text value.

## F. Execution Flow
Imported by other modules. Nothing runs here.

## G. Input and Output
None.

## H. Important Technical Concepts
- **Three kinds of truth stay separate (PRD 6.1).** `PredictionDecision` is the model's output, `InvestigationStatus` is a person's workflow label, and ground-truth labels live in their own table. None is derived from another.
- **`FALSE_ALARM` is a workflow outcome.** It records an investigator's conclusion and does not feed back into any metric.

## I. Example
```python
PredictionDecision.FLAG_FOR_REVIEW == "FLAG_FOR_REVIEW"  # True
```

## J. Maintenance Notes
Adding a value needs a migration, since the CHECK constraint lists allowed values.

## K. Related Files
- [base.py](../database/base.py.explanation.md): `enum_type`.
- [permissions.py](../security/permissions.py.explanation.md): what each role may do.
- [ADR 0003](../../../docs/decisions/0003-phase-3-decisions.md): decisions 3, 4 and 7.
