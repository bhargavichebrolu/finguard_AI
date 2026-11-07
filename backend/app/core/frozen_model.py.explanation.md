# frozen_model.py

Source: [backend/app/core/frozen_model.py](frozen_model.py)

## A. File Purpose
Records in code which model is approved for serving, along with its file hash, threshold and the wording that describes its scores.

## B. Why This File Exists
The Phase 3 authorisation forbids changing the selected model or threshold. Metadata alone cannot guarantee that, because someone could change a model file and its metadata together. A hash in version-controlled code means any change to the served model is a visible code change.

## C. Dependencies
- **Libraries:** none.
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** `model_service.py` and the prediction response schemas.

## D. Every Function Explained
No functions. The constants:

### `FROZEN_MODEL_VERSION`, `FROZEN_MODEL_SHA256`, `FROZEN_THRESHOLD`
Copied from `artifacts/metadata/model_v1.json`, which was committed at the Phase 2 freeze (`324e30d`).

### `VERIFIED_LIBRARIES`
Libraries whose installed version must equal the one recorded when the model was saved.

### `SCORE_TYPE`, `SCORE_IS_CALIBRATED`, `SCORE_NOTE`
Returned with every prediction, so API users always see that the score is uncalibrated and that a flag is not a finding of fraud.

## E. Classes Explained
None.

## F. Execution Flow
Imported at start-up. `model_service.py` compares these values with the metadata and the model file.

## G. Input and Output
No input. Output: constants.

## H. Important Technical Concepts
- **Why the score is not a probability.** Phase 2 found that validation rows scoring 0.1 to 0.2 were fraud 31% of the time. The score also reflects the training period's fraud rate, which differs from other periods.
- **Exact float.** The threshold is stored at full precision. Rounding could move rows across the line, because scores cluster tightly near it.

## I. Example
```python
from app.core.frozen_model import FROZEN_THRESHOLD

score >= FROZEN_THRESHOLD  # True means FLAG_FOR_REVIEW
```

## J. Maintenance Notes
Change these values only when deliberately releasing a new model. That needs a new version folder, new metadata and new evaluation.

## K. Related Files
- [model_service.py](../services/model_service.py.explanation.md): enforces these values.
- [ADR 0003](../../../docs/decisions/0003-phase-3-decisions.md): decisions 2, 3 and 13.
