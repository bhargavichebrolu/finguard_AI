# PredictionResult.tsx

Source: [frontend/src/components/PredictionResult.tsx](PredictionResult.tsx)

## A. File Purpose
Shows the outcome of scoring one transaction: decision, risk band, uncalibrated score, risk score, threshold and boundary used, model version and investigation.

## B. Why This File Exists
PRD 6.2 and 6.6 list these fields, and the authorisation requires the score to be identified as uncalibrated and the decision as a request for review.

## C. Dependencies
- **Libraries:** React.
- **Internal modules:** `badges.tsx`, `../utils/format.ts`, `../services/endpoints.ts`.
- **External services / database:** none.
- **Depended on by:** Transaction Analysis, transaction detail.

## D. Every Function Explained

### `PredictionResult`
Renders the fields above, labelling the score "Model score (uncalibrated)" and the risk score "not a percentage", and repeats the API's `score_note`. Demo records carry the demo badge.

## E. Classes Explained
None.

## F. Execution Flow
Rendered after a successful prediction.

## G. Input and Output
Input: a `Prediction`. Output: an `<article>` labelled "Prediction result".

## H. Important Technical Concepts
- **Settings that produced it:** the threshold and high risk boundary come from the stored prediction, so old results remain interpretable after a settings change.

## I. Example
```tsx
<PredictionResult prediction={result} />
```

## J. Maintenance Notes
Do not display the score with a percent sign. `format.ts` and tests enforce this.

## K. Related Files
- [format.ts](../utils/format.ts.explanation.md): wording.
- [badges.tsx](badges.tsx.explanation.md): labels.
