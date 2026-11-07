# risk.py

Source: [backend/app/services/risk.py](risk.py)

## A. File Purpose
Converts a model score into a decision (`FLAG_FOR_REVIEW` or `NOT_FLAGGED`), a risk level and a risk score.

## B. Why This File Exists
PRD 6.3 asks for configurable risk boundaries, while the authorisation forbids changing the threshold. This small pure function is where those two requirements are reconciled, so it can be tested fully on its own.

## C. Dependencies
- **Libraries:** `dataclasses`.
- **Internal modules:** `app.models.enums`.
- **External services / database:** none.
- **Depended on by:** `prediction_service.py`, `settings_service.py`.

## D. Every Function Explained

### `assess_score`
- **Purpose:** classify one score.
- **Parameters / types:** `score: float`, `threshold: float`, `high_boundary: float`. **Returns / type:** `RiskAssessment`.
- **Internal processing:** below the threshold is Low and not flagged, from there to the boundary is Medium and flagged, and at or above the boundary is High and flagged. `risk_score` is `score * 100`.
- **Error handling:** raises `ValueError` if the boundary is not above the threshold, since Medium would then be empty and High would take in unflagged rows.
- **Calls:** none. **Used by:** `prediction_service`.

## E. Classes Explained

### `RiskAssessment`
- **Purpose:** the classification of one score.
- **Attributes:** `decision`, `risk_level`, `risk_score`.
- **Methods:** none.
- **Inheritance:** none; a frozen dataclass.

## F. Execution Flow
Called once for each scored row.

## G. Input and Output
Example with threshold 0.02842 and boundary 0.30: score 0.01 gives `NOT_FLAGGED`, `LOW`, 1.0. Score 0.05 gives `FLAG_FOR_REVIEW`, `MEDIUM`, 5.0. Score 0.9 gives `FLAG_FOR_REVIEW`, `HIGH`, 90.0.

## H. Important Technical Concepts
- **`risk_score` is not a percentage chance.** It is the uncalibrated score on a 0 to 100 scale, and a flagged row can show 2.84.
- **At the threshold counts as flagged,** matching `>=` in Phase 2's evaluation, so the frozen results apply to what is served.
- **Measured performance:** at this threshold on test, 40.7% of flags were labelled fraud and 45.9% of labelled fraud was flagged (21.9% in normal steps). The false positive rate was 0.282% against a 0.1% target.

## I. Example
```python
assess_score(0.05, 0.02841914258897305, 0.30).risk_level  # RiskLevel.MEDIUM
```

## J. Maintenance Notes
Do not add a calibrated interpretation here without measuring calibration first (PRD 6.3).

## K. Related Files
- [ADR 0003](../../../docs/decisions/0003-phase-3-decisions.md): decisions 4 and 5.
- [enums.py](../models/enums.py.explanation.md): the vocabularies.
- [test_model_service.py](../../tests/unit/test_model_service.py.explanation.md): tests.
