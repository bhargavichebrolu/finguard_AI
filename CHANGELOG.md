# Changelog

## Phase 2: Machine learning experiments (2026-11-07)

### Added
- Six model families and four imbalance strategies, with oversampling confined to training folds.
- A selection rule and threshold objective, committed before any candidate was scored.
- Temporal drift analysis, a label-independent definition of sparse steps, threshold analysis, TreeSHAP explanations, and a single guarded test evaluation.
- Hash-verified model loading that imports no training code.
- 322 backend tests: 301 on synthetic data and 21 on real outputs. All passed, none skipped.

### Results
- 125 runs recorded on validation, none failed.
- Selected: XGBoost on the original distribution, threshold 0.02842. XGBoost, LightGBM and CatBoost were statistically tied on validation.
- Test, evaluated once: PR-AUC 0.4242, ROC-AUC 0.9524, precision 40.7%, recall 45.9%, false positive rate 0.282%.
- Recall was 56.1% in sparse steps and 21.9% in normal steps.

### Fixed
- `final_evaluation.py` labelled the commit the model was fitted from as the freeze commit, found on review before test was opened. The field was renamed and the tests now check Git history.
- Generated tables left out the sensitivity runs and listed partitions alphabetically.
- Chart label collisions and unreadable text in confusion matrices.
- `KeyError`s in reports for empty slices, found by testing on real outputs.

### Known limitations
- The false positive rate on test was 2.8 times the 0.1% cap set on validation.
- Validation overstated results in sparse steps (recall 95.6% against 56.1% on test). The likely cause, reliance on hour, is not confirmed.
- LightGBM's matrix results on the original distribution and class weighting reflect a numerical divergence, not those strategies. See `ML_EXPERIMENTS.md`.
- Scores are not calibrated probabilities.
- Phase 2 peak memory was not measured.
- PaySim has no untouched window left, so a revised model could not be fairly measured on it.

## Phase 1: Foundation and data engineering (2026-11-06)

### Added
- Repository structure from PRD section 13, with later-phase folders held empty.
- Python 3.11 environment with uv, and the full training stack verified to import.
- React, TypeScript and Vite toolchain, with a placeholder page.
- Streaming dataset validation, EDA, feature engineering, leakage audit and chronological partitioning.
- 89 backend tests, including tamper tests that prove the audit and documentation checker can fail.
- Documentation checker that enforces PRD section 12, and an explanation document for every source file.
- All documents required by PRD 12.4, with unbuilt parts clearly marked as planned.

### Results
- Dataset verified: 6,362,620 rows, 8,213 fraud rows, no missing values or duplicates.
- Partitions: train steps 1 to 322, validation 323 to 377, test 378 to 743.
- Preprocessing reproduced byte-identically on rerun.

### Fixed
- A floating-point error in split boundary selection, found by a unit test. It did not affect the real boundaries.
- Security advisories, by moving to React Router 7 and Vite 8 before any page used them.

### Known limitations
- `make` and Docker are not installed on the development machine, so the `Makefile` is unexecuted as a file and no container exists.
- The successful Kaggle download route has not been run, as no token is available.
- The frontend has no automated tests yet.
