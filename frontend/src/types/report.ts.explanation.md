# report.ts

Source: [frontend/src/types/report.ts](report.ts)

## A. File Purpose
Typed views of the model report's sections, and a helper that pairs curve arrays into chart points.

## B. Why This File Exists
The API declares the report's sections as general JSON, because they are copied unchanged from saved Phase 2 files of different shapes. The page needs named fields, so this file states the shape it relies on in one place.

## C. Dependencies
- **Libraries:** none.
- **Internal modules:** `../services/endpoints.ts` for `ModelReport`.
- **External services / database:** none.
- **Depended on by:** `ModelPerformancePage.tsx`, tests.

## D. Every Function Explained

### `readReport`
- **Purpose:** give each report section its type.
- **Parameters / types:** `report: ModelReport`. **Returns / type:** `TypedReport`.
- **Internal processing:** renames the sections for the page and casts each to its interface. Nothing is changed or calculated.
- **Error handling:** none; the backend's report checks guarantee the shape. **Calls:** none. **Used by:** the page.

### `toPoints`
Pairs two arrays of the same length, such as recall and precision, into `{x, y}` points.

## E. Classes Explained
### `Curves, AtThreshold, Interval, FamilyRow, HistoryRow, MatrixCell, Confusion, Decision, TypedReport`
Interfaces, not classes. Each names the fields one section provides. `AtThreshold` is the set of measures at one threshold. `TypedReport` gathers them all.

## F. Execution Flow
Called once per report load.

## G. Input and Output
Input: the API's report. Output: the same data under typed names.

## H. Important Technical Concepts
- **Casts, not checks:** these casts trust the backend, whose `test_model_report.py` compares every value with its source file and pins the report's hash.

## I. Example
```ts
const { families, decision } = readReport(report);
```

## J. Maintenance Notes
Keep these field names identical to `scripts/export_model_report.py`.

## K. Related Files
- [ModelPerformancePage.tsx](../pages/ModelPerformancePage.tsx.explanation.md): the only page using it.
