# ModelPerformancePage.tsx

Source: [frontend/src/pages/ModelPerformancePage.tsx](ModelPerformancePage.tsx)

## A. File Purpose
Page 6 of PRD 7.4, covering PRD 6.8: the saved Phase 2 results, including the model comparison, curves, confusion matrices, threshold comparison, imbalance strategies, training and inference cost, and the experiment history.

## B. Why This File Exists
PRD 6.8 asks for a comparison of every model with PR-AUC, ROC-AUC, precision, recall, F1, balanced accuracy, confusion matrices, curves and timings. Authorisation decision 5 requires every value to come from saved Phase 2 outputs, with nothing retrained, recalculated or re-read from `data/`.

## C. Dependencies
- **Libraries:** React.
- **Internal modules:** `../components/charts.tsx`, `DataTable.tsx`, `feedback.tsx`, `ScoreDisclosure.tsx`, `../hooks/useApiResource.ts`, `../services/endpoints.ts`, `../types/report.ts`, `../utils/format.ts`.
- **External services / database:** `GET /api/v1/models/report`, and `GET /api/v1/models/metrics` through the disclosure.
- **Depended on by:** `registry.tsx`.

## D. Every Function Explained

### `familyName`
Returns the readable name of a model family, such as `xgboost` to XGBoost. Unknown names are humanised.

### `ruleName`
Returns the readable name of an alternative threshold rule: `fpr_cap_0.001` becomes "False positive rate at most 0.001" and `max_f1` becomes "Highest F1".

### `decimal`
Formats a number to a fixed number of places, or a dash when it is missing.

### `ModelPerformancePage`
- **Purpose:** load the report and show the page.
- **Parameters / types:** none. **Returns / type:** a section.
- **Internal processing:** shows the score disclosure, then loading, error or content.
- **Error handling:** an error state with retry. **Calls:** `modelsApi.report`, `readReport`. **Used by:** the registry.

### `PerformanceContent`
Lays out the notes from the report, every section below, and the list of source files with the start of each SHA-256 hash.

### `FamilyComparison`
A table of each family's best validation run: strategy, PR-AUC with its 95% interval, ROC-AUC, and precision, recall, F1, balanced accuracy and false positive rate at that model's own threshold at the false positive rate cap. The selected family is badged Selected, and the families that were statistically tied are badged Tied. A PR-AUC bar chart follows. Accuracy is deliberately not shown on its own.

### `CurveSection`
Precision-recall and ROC curves for the selected model on validation and test, and a selector that compares any family's validation curve with the selected model's. Each chart has a table view listing the number of points, because a table of hundreds of curve points would not help a reader.

### `ConfusionTable`
One confusion matrix as a table with row and column headers: labelled fraud or legitimate, against flagged or not flagged.

### `ConfusionSection`
Validation, test and test split by step type (normal and sparse), all at the frozen threshold.

### `ThresholdSection`
Compares the frozen threshold with the alternative rules and the PRD candidate thresholds on validation, then plots precision and recall across the threshold sweep on a log axis. The sweep's zero-threshold row is dropped, because a log axis cannot show zero.

### `CostSection`
Training time and single-row inference time by family as bar charts, with batch time per row in the table view.

### `MatrixSection`
PR-AUC on validation for every family and imbalance strategy, as a table, with the LightGBM divergence note.

### `HistorySection`
All recorded runs in pages of 25, with a stage filter that returns to the first page when changed.

### `names`
A local value in `familyName`, not a function: the lookup of readable names.

## E. Classes Explained
None.

## F. Execution Flow
Load the report once, convert it with `readReport`, then render each section from it. Nothing is computed beyond formatting and filtering.

## G. Input and Output
Input: the report. Output: tables and charts. There are no user inputs apart from the family selector, the history stage filter and paging.

## H. Important Technical Concepts
- **Validation and test:** validation figures guided every choice. Test figures come from the one evaluation after the freeze. The page labels every section with its partition.
- **Two series per chart:** `CurveChart` takes at most two series, because only that pair of colours passed the palette check together. Comparing six families on one chart would need colours that fail it, so the page compares one family at a time with the selected model.
- **Ties are shown as ties:** the notes and badges say the top families were statistically indistinguishable, rather than presenting one as better.
- **No hard-coded figures:** the source-rules test scans `src/` for the saved Phase 2 values, so every number must come from the API.

## I. Example
```tsx
const report = useApiResource(() => modelsApi.report(), []);
{report.data ? <PerformanceContent report={readReport(report.data)} source={report.data.source_files} /> : null}
```

## J. Maintenance Notes
If the report gains a section, add its type to `report.ts` first. Keep the partition named on every section.

## K. Related Files
- [report.ts](../types/report.ts.explanation.md): the typed sections.
- [export_model_report.py](../../../scripts/export_model_report.py.explanation.md): how the report is built from saved files.
- [charts.tsx](../components/charts.tsx.explanation.md): `CurveChart`.
