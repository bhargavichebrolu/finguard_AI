# test_schema.py

Source: [backend/tests/unit/test_schema.py](../../../../../backend/tests/unit/test_schema.py)

## A. File Purpose
Tests that the declared feature schema obeys the leakage rules in PRD 4.3 and the documentation rule in PRD 4.4.

## B. Why This File Exists
A one-line edit to `schema.py` could reintroduce leakage. These tests fail immediately if it does.

## C. Dependencies
- **Libraries:** `json`.
- **Internal modules:** `app.ml.schema`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained
**Common to every test below:** no parameters, returns `None`, failures surface as `AssertionError`, and pytest calls them. No project code uses them.

| Function | Proves |
|---|---|
| `test_features_exclude_every_forbidden_column` | No feature is in `FORBIDDEN_FEATURE_COLUMNS`. |
| `test_target_and_rule_flag_are_forbidden` | `isFraud` and `isFlaggedFraud` are in the forbidden set. |
| `test_pipeline_never_reads_balances_or_origin_account` | The read allow-list excludes balances and `nameOrig`. |
| `test_identifiers_are_not_features` | Account identifiers are not features. |
| `test_every_feature_is_available_before_completion` | Every feature is flagged as available at assessment time. |
| `test_every_feature_has_complete_documentation` | Each dictionary row has all its fields and valid source columns. |
| `test_numeric_and_categorical_lists_cover_all_features_once` | Each feature has exactly one kind. |
| `test_feature_dictionary_records_are_json_serialisable` | `feature_dictionary_records` survives a JSON round trip, in feature order. |

## E. Classes Explained
None.

## F. Execution Flow
pytest imports the module and runs each test. The tests read constants, so no data is needed.

## G. Input and Output
Input: schema constants. Output: pass or fail.

## H. Important Technical Concepts
These tests protect the schema's declarations. The file-level check that the declarations were actually obeyed is in `test_data_pipeline.py`.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_schema.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
If a test here fails after a schema edit, treat that as a leakage alarm and do not simply update the test.

## K. Related Files
- [schema.py](../../app/ml/schema.py.explanation.md): code under test.
