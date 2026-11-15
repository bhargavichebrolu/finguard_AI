# test_transactions.py

Source: [backend/tests/api/test_transactions.py](test_transactions.py)

## A. File Purpose
Tests scoring, storage, wording, input validation and the explorer through the real API, the real model and real PostgreSQL.

## B. Why This File Exists
PRD 14.2 requires tests of input validation, the prediction endpoint and invalid requests. The authorisation's terms also need proof: stored model version and threshold, uncalibrated labelling, and `FLAG_FOR_REVIEW`.

## C. Dependencies
- **Libraries:** `pytest`, `numpy`, `pandas`, `sqlalchemy`.
- **Internal modules:** `app.core`, `app.models`, API fixtures.
- **External services / database:** PostgreSQL and the frozen model. Inputs are hand-written, and no test partition data is used.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `analyst`
Fixture returning headers for an analyst.

### `_store_samples`
Stores four known transactions with fixed identifiers, for explorer tests.

### `_identifiers`
Returns the identifiers in a list response.

**Common to every test below:** failures surface as `AssertionError`. pytest runs them.

| Function | Proves |
|---|---|
| `test_flagged_prediction_has_every_required_field` | The score, its uncalibrated labelling, version, threshold and new investigation. |
| `test_unflagged_prediction_is_low_and_has_no_investigation` | Low means not flagged, with no investigation opened. |
| `test_api_score_equals_the_model_called_directly` | The API adds nothing to the score. |
| `test_prediction_is_stored_with_model_version_and_threshold` | The stored row records what produced it. |
| `test_stored_amount_is_exact` | Amounts keep their exact decimals. |
| `test_prediction_is_audited` | An audit entry is written. |
| `test_explanation_is_returned_and_adds_up` | Contributions reproduce the score, and the causality warning is present. |
| `test_no_response_or_schema_uses_probability_wording` | The forbidden wording does not appear. |
| `test_invalid_values_are_refused` | Bad values give 422 and store nothing. |
| `test_each_input_is_required` | All four inputs are needed. |
| `test_combinations_absent_from_training_are_refused` | Merchant only with PAYMENT, and the reverse. |
| `test_labels_and_leaky_fields_are_refused` | `isFraud`, balances and account names are refused. |
| `test_unsafe_identifiers_are_refused` | Spreadsheet formula characters and over-long identifiers are refused. |
| `test_repeated_identifier_is_a_conflict_and_stores_nothing_new` | 409 and no partial records. |
| `test_identifier_is_generated_when_omitted` | An identifier is created when none is supplied. |
| `test_prediction_rate_limit` | The per-user limit applies. |
| `test_explorer_filters` | Each PRD 6.5 filter, including that `%` is treated literally. |
| `test_explorer_rows_never_mix_scores_and_labels` | Rows hold no label or fraud field. |
| `test_explorer_sorting` | Sort fields and directions. |
| `test_explorer_sorts_by_score` | Scores come back in order. |
| `test_explorer_pagination_is_complete_and_stable` | Pages cover every row once, and unknown sort fields are refused. |
| `test_explorer_pages_match_one_full_sort` | Phase 6 deferred join: for each sort field and direction, with no filter, an investigation filter and a type filter, one-row pages walked in turn equal the single full page exactly. |
| `test_detail_view_has_prd_fields` | The PRD 6.6 fields are present. |
| `test_unknown_transaction_is_not_found` | 404. |
| `test_demo_records_are_labelled_and_kept_apart` | Demo records are marked and separated both ways, with no investigation. |

## E. Classes Explained
None.

## F. Execution Flow
The `session` fixture empties the database before each test.

## G. Input and Output
Input: HTTP requests. Output: pass or fail.

## H. Important Technical Concepts
- **`HIGH_SCORING` and `LOW_SCORING` rely on the frozen model.** Their expected decisions were checked against it, and tests assert them. These are not samples of test data.

## I. Example
```powershell
uv run --project backend pytest backend/tests/api/test_transactions.py
```

## J. Maintenance Notes
A new model could change which side of the threshold these examples fall on.

## K. Related Files
- [transactions.py route](../../app/api/routes/transactions.py.explanation.md): routes.
- [prediction_service.py](../../app/services/prediction_service.py.explanation.md): the logic.
