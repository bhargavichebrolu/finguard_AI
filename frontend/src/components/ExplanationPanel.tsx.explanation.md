# ExplanationPanel.tsx

Source: [frontend/src/components/ExplanationPanel.tsx](ExplanationPanel.tsx)

## A. File Purpose
Shows how each input moved one score, by input group and by model input, with the limits of what that shows.

## B. Why This File Exists
PRD 6.2 and 6.6 ask for explanations where supported, and PRD 5.7 forbids presenting SHAP as causal. The panel always shows the limitations the API returns with the explanation.

## C. Dependencies
- **Libraries:** React.
- **Internal modules:** `charts.tsx`, `../services/endpoints.ts`, `../utils/format.ts`.
- **External services / database:** none.
- **Depended on by:** Transaction Analysis, Explainable AI, transaction detail.

## D. Every Function Explained

### `featureLabel`
Turns encoded model inputs into words, for example `transaction_type_TRANSFER` into "Type is TRANSFER", and `hour_sin` into "Hour of day (sine)".

### `ExplanationPanel`
- **Purpose:** render one explanation.
- **Parameters / types:** `explanation`, which may be missing. **Returns / type:** a section.
- **Internal processing:** draws group contributions as bars either side of zero, lists every model input's contribution, and states the base value, scale and method.
- **Error handling:** with no stored explanation it explains why: batch rows have one only when flagged.
- **Calls:** `ContributionBars`, `featureLabel`. **Used by:** pages.

## E. Classes Explained
None.

## F. Execution Flow
Receives the explanation from a prediction or transaction detail response.

## G. Input and Output
Input: `base_value`, `by_group`, `by_feature`, `limitations`. Output: a chart, a table and a list of limits.

## H. Important Technical Concepts
- **Log-odds:** contributions add to the base value on the log-odds scale, which the logistic function turns into the score. The scale is named on screen.

## I. Example
```tsx
<ExplanationPanel explanation={prediction.explanation} />
```

## J. Maintenance Notes
Keep the limitations visible wherever an explanation is shown.

## K. Related Files
- [model_service.py](../../../backend/app/services/model_service.py.explanation.md): computes explanations.
- [charts.tsx](charts.tsx.explanation.md): the chart.
