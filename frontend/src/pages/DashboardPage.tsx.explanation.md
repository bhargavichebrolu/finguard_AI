# DashboardPage.tsx

Source: [frontend/src/pages/DashboardPage.tsx](DashboardPage.tsx)

## A. File Purpose
Page 1 of PRD 7.4, covering PRD 6.1: model flags, investigation workflow, uploaded labels, model performance and recent activity.

## B. Why This File Exists
PRD 6.1 lists these figures and forbids mixing ground-truth labels, model predictions and investigation outcomes. Each has its own section, and every number comes from the API.

## C. Dependencies
- **Libraries:** React, React Router.
- **Internal modules:** components, `../hooks`, `../services/endpoints.ts`, `../utils/format.ts`.
- **External services / database:** `GET /api/v1/reports/summary`, and the metrics already loaded by `useModelLimits`.
- **Depended on by:** `registry.tsx`.

## D. Every Function Explained

### `DashboardPage`
Loads the summary, shows the compact disclosure, and handles loading and error states.

### `DashboardContent`
- **Purpose:** lay out the summary.
- **Parameters / types:** `summary: SummaryReport`. **Returns / type:** sections.
- **Internal processing:** six stat tiles. Charts for risk bands, analysed and flagged by type, and flagged per simulated day, each with a table view. Then the workflow counts, uploaded labels, the performance summary and recent predictions.
- **Error handling:** an empty scope shows a message instead of empty charts. **Calls:** chart components. **Used by:** `DashboardPage`.

### `ModelPerformanceSummary`
Shows test recall, normal-step recall, precision and false positive rate against its target, from the saved metrics, with a link to Model Performance.

## E. Classes Explained
None.

## F. Execution Flow
Summary loads, then each section renders from it.

## G. Input and Output
Output: the dashboard.

## H. Important Technical Concepts
- **Wording:** PRD 6.1 says "fraudulent predictions" and "fraud rate". The dashboard says "flagged for review" and "share flagged", because a flag is not fraud, and a fraud rate could only come from labels.
- **Demo scope** is labelled when the user is a demo user (PRD 7.6).
- **Evaluation figures are labelled** as a single test evaluation after the freeze.

## I. Example
```tsx
<DashboardPage />
```

## J. Maintenance Notes
Never compute a performance figure here. Show what the API returns.

## K. Related Files
- [report_service.py](../../../backend/app/services/report_service.py.explanation.md): builds the summary.
- [charts.tsx](../components/charts.tsx.explanation.md): charts.
