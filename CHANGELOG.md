# Changelog

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
