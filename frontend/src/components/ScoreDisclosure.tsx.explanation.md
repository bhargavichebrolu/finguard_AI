# ScoreDisclosure.tsx

Source: [frontend/src/components/ScoreDisclosure.tsx](ScoreDisclosure.tsx)

## A. File Purpose
The statement shown beside model scores: what a score is, what a flag means, and the model's measured limitations.

## B. Why This File Exists
The authorisation requires the interface never to present the score as a probability, and to disclose the measured recall and false positive rate limitations clearly.

## C. Dependencies
- **Libraries:** React, `lucide-react`.
- **Internal modules:** `../hooks/useModelLimits.tsx`.
- **External services / database:** none directly.
- **Depended on by:** Dashboard, Transaction Analysis, batch results, transaction detail, Model Performance.

## D. Every Function Explained

### `ScoreDisclosure`
- **Purpose:** render the disclosure.
- **Parameters / types:** `compact?: boolean`, which shows the first three notes. **Returns / type:** a React element.
- **Internal processing:** always shows `SCORE_MEANING`, then the notes from the API.
- **Error handling:** if the notes fail to load, it shows a warning instead of silently omitting them.
- **Calls:** `useModelLimits`. **Used by:** pages.

## E. Classes Explained
None.

## F. Execution Flow
Reads the notes loaded once per session and renders them.

## G. Input and Output
Output: an `<aside>` labelled "How to read model scores".

## H. Important Technical Concepts
- **The fixed sentence holds no figure.** Every number comes from the API, built from the saved metrics file.

## I. Example
```tsx
<ScoreDisclosure compact />
```

## J. Maintenance Notes
If the wording changes, keep the words "not calibrated" and "not a finding". Browser tests look for the disclosure on every page that shows a score.

## K. Related Files
- [useModelLimits.tsx](../hooks/useModelLimits.tsx.explanation.md): the data.
- [metrics_service.py](../../../backend/app/services/metrics_service.py.explanation.md): where the sentences are built.
