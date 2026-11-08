# ExplainabilityPage.tsx

Source: [frontend/src/pages/ExplainabilityPage.tsx](ExplainabilityPage.tsx)

## A. File Purpose
Page 7 of PRD 7.4: saved global importance from Phase 2, and the stored explanation of any recent prediction.

## B. Why This File Exists
PRD 6.8 and 5.7 ask for feature importance and explanations, with their limits. Global figures come from the saved analysis, and nothing is recalculated.

## C. Dependencies
- **Libraries:** React.
- **Internal modules:** components, `../hooks/useApiResource.ts`, `../services/endpoints.ts`.
- **External services / database:** `GET /api/v1/models/feature-importance`, `GET /api/v1/transactions`, `GET /api/v1/transactions/{id}`.
- **Depended on by:** `registry.tsx`.

## D. Every Function Explained

### `ExplainabilityPage`
Shows importance by input group as a chart with a table, importance by model input as a table, and the saved limitations.

### `LocalExplanations`
Lists the ten most recent predictions. Opening one loads its detail and shows its stored explanation.

## E. Classes Explained
None.

## F. Execution Flow
Importance loads on open, and a chosen prediction loads on demand.

## G. Input and Output
Output: global and local explanations.

## H. Important Technical Concepts
- **Global versus local:** global importance summarises the validation sample used in Phase 2. A local explanation describes one score only.

## I. Example
```tsx
<ExplainabilityPage />
```

## J. Maintenance Notes
Keep the limitations in view on this page.

## K. Related Files
- [ExplanationPanel.tsx](../components/ExplanationPanel.tsx.explanation.md): local view.
- [metrics_service.py](../../../backend/app/services/metrics_service.py.explanation.md): saved importance.
