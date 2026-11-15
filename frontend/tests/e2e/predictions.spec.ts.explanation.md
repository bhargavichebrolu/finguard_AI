# predictions.spec.ts

Source: [frontend/tests/e2e/predictions.spec.ts](predictions.spec.ts)

## A. File Purpose
Tests scoring one transaction: validation in the page and in the API, how the score is shown and worded, the disclosed limitations, and the stored record.

## B. Why This File Exists
The standing rules forbid presenting the uncalibrated score as a fraud probability and require the measured recall and false positive rate shortfalls to be disclosed. These tests check both in the browser.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `support.ts`.
- **External services / database:** The browser-test API on 127.0.0.1:8011 and the finguard_e2e_test database, through the preview server on 127.0.0.1:4173.
- **Depended on by:** none; run by `npm run test:e2e`.

## D. Every Function Explained

### `expectNoProbabilityClaims`
Splits the page text into sentences and fails on any that mentions probability, chance or likelihood without denying it.

### `fillForm`
Fills the four form fields and the optional identifier.

### `scoreThroughForm`
Submits the form and returns the API's stored prediction, so displayed values can be compared with it.

### `multiple`
A local value, not a function: the test false positive rate divided by the target, to one decimal place.

### `served`
A local value, not a function: the notes the metrics route serves.

## E. Classes Explained
None.

## F. Execution Flow
Each test signs in through a saved state and works through the real interface and API.

## G. Input and Output
| Test | Proves |
|---|---|
| refuses invalid inputs with field messages, without calling the API | Messages, `aria-invalid`, no request. |
| shows the API's own refusals | Duplicate identifier message; 422 for a merchant mismatch, a zero amount and an extra label field. |
| presents a flagged score as an uncalibrated number with its settings | Four decimals, "uncalibrated", risk score not a percentage, threshold from `model_v1.json`, model version, New investigation, no probability claims, no console or CSP errors. |
| presents an unflagged score without opening an investigation | Not flagged, none opened. |
| discloses the measured limitations exactly as saved | Figures recomputed from `model_v1_metrics.json` appear; the first three notes beside scores, all notes on Model Performance. |
| stores the prediction and shows it in the explorer | Filter, row and detail match the stored score. |

## H. Important Technical Concepts
- **Expected figures come from the saved file,** formatted as the API formats them, so the test catches any change in wording or number.

## I. Example
```powershell
npm run test:e2e -- tests/e2e/predictions.spec.ts --project=setup --project=desktop
```

## J. Maintenance Notes
If a note's wording changes in `metrics_service.py`, update the recomputed sentences here.

## K. Related Files
- [support.ts](support.ts.explanation.md): shared helpers.
- [ScoreDisclosure.tsx](../../src/components/ScoreDisclosure.tsx.explanation.md): the disclosure.
