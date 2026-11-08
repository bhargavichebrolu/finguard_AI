# format.ts

Source: [frontend/src/utils/format.ts](format.ts)

## A. File Purpose
Defines how scores, rates, amounts, counts, dates and API values are written on screen.

## B. Why This File Exists
The authorisation forbids presenting the uncalibrated score as a probability. Writing every score through one function, with no percent sign, makes that rule testable.

## C. Dependencies
- **Libraries:** none (built-in `Intl`).
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** components and pages.

## D. Every Function Explained

### `formatScore`
Writes a score to four decimal places, for example `0.8377`, never with `%`. Missing values show as a dash.

### `formatRiskScore`
Writes the 0 to 100 risk score with the words "score × 100, not a percentage".

### `formatRate`
Writes a measured proportion, such as recall, as a percentage, with chosen decimals.

### `formatAmount`
Writes an amount with two decimals and thousands separators.

### `formatCount`
Writes a whole number with thousands separators.

### `formatDateTime`
Writes a timestamp in the reader's time zone.

### `humanise`
Turns `UNDER_REVIEW` into "Under review".

### `describeDecision`
Writes `FLAG_FOR_REVIEW` as "Flagged for review", and the other decision as "Not flagged".

## E. Classes Explained
None.

## F. Execution Flow
Called while rendering.

## G. Input and Output
Input: raw API values. Output: display strings.

## H. Important Technical Concepts
- **Score versus rate:** a model score is a ranking value and gets no percent sign. Recall and false positive rates are measured proportions, so percentages are correct for them.

## I. Example
```ts
formatScore(0.8377037048339844); // "0.8377"
```

## J. Maintenance Notes
Do not add a percentage formatter for scores. `foundation.test.tsx` checks this.

## K. Related Files
- [badges.tsx](../components/badges.tsx.explanation.md): uses `humanise` and `describeDecision`.
- [foundation.test.tsx](../../tests/unit/foundation.test.tsx.explanation.md): tests.
