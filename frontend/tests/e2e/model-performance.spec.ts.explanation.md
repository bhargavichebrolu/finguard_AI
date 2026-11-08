# model-performance.spec.ts

Source: [frontend/tests/e2e/model-performance.spec.ts](model-performance.spec.ts)

## A. File Purpose
Checks that Model Performance shows the saved Phase 2 results unchanged, by comparing the page with the original saved files.

## B. Why This File Exists
Authorisation decision 5 requires the page to come only from saved Phase 2 outputs, with nothing retrained or recalculated and nothing read from `data/`.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `support.ts`.
- **External services / database:** The browser-test API on 127.0.0.1:8011 and the finguard_test database, through the preview server on 127.0.0.1:4173.
- **Depended on by:** none; run by `npm run test:e2e`.

## D. Every Function Explained

### `count`
Formats a count with thousands separators, as the page does.

### `rate`
Formats a proportion as a percentage, as the page does.

### `openPage`
Opens the page and waits for the comparison table.

## E. Classes Explained
None.

## F. Execution Flow
Each test signs in through a saved state and works through the real interface and API.

## G. Input and Output
| Test | Proves |
|---|---|
| every saved source file still matches the hash the report records | The six source files are byte-for-byte unchanged. |
| shows each family's validation results as saved in selection.json | PR-AUC, 95% intervals, ROC-AUC, precision, recall and false positive rate per family; Selected and Tied badges; the report notes. |
| keeps validation and test apart, with test counts from test_evaluation.json | Test, normal-step and sparse-step confusion counts from the test file; validation counts from the metrics file; frozen threshold row. |
| draws both curves per chart and offers their data as a table | Two drawn curves, the table view and the family comparison. |
| lists every recorded run from all_runs.csv, by stage | Run count, page of run ids and the stage filter. |
| only reads: no changes, no retraining, nothing from the dataset folder | Only three GET requests, none to `data/`. |

## H. Important Technical Concepts
- **Sources, not the report:** comparing with `selection.json`, `test_evaluation.json`, `model_v1_metrics.json` and `all_runs.csv` checks the whole chain, not just the derived report.

## I. Example
```powershell
npm run test:e2e -- tests/e2e/model-performance.spec.ts --project=setup --project=desktop
```

## J. Maintenance Notes
These files are frozen; if a test here fails, a frozen result changed, which the authorisation forbids.

## K. Related Files
- [support.ts](support.ts.explanation.md): shared helpers.
- [export_model_report.py](../../../scripts/export_model_report.py.explanation.md): how the report is built.
