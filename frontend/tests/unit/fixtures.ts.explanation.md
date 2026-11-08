# fixtures.ts

Source: [frontend/tests/unit/fixtures.ts](fixtures.ts)

## A. File Purpose
Builds realistic API responses for component tests, typed against the generated API types.

## B. Why This File Exists
Typed fixtures break the build when the API changes, rather than letting tests pass against an outdated shape.

## C. Dependencies
- **Libraries:** none.
- **Internal modules:** `../../src/services/endpoints.ts` types.
- **External services / database:** none.
- **Depended on by:** `server.ts`, tests.

## D. Every Function Explained

### `userFixture`
Returns a signed-in user for a role, with the same permission lists as the API's role table and a session expiring in 30 minutes.

### `metricsFixture`
Returns a metrics response whose notes are clearly labelled test sentences, not real figures.

### `statusFixture`
Returns a healthy system status.

### `predictionFixture`
Returns a flagged prediction with an explanation, using fixture values only.

### `summaryFixture`
Returns a summary. `empty` gives a scope with no records, and `demo` marks it as demo.

### `featureImportanceFixture`
Returns saved-importance data with a labelled fixture limitation.

### `settingsFixture`
Returns settings with small upload limits (1,000 bytes, 50 rows), so limit checks are easy to trigger.

### `batchFixture`
Returns a finished batch job with one refused row and an ignored `isFraud` column. Fields can be overridden.

### `fixtureAt`
Returns the measures at one threshold, with invented values.

### `fixtureFamily`
Returns one family's comparison row, with invented values.

### `reportFixture`
Returns a small model report with the real section shape and invented values: three families, curves, confusion matrices, thresholds, two matrix cells and two history runs.

## E. Classes Explained
None.

## F. Execution Flow
Called by the mock handlers.

## G. Input and Output
Output: typed objects.

## H. Important Technical Concepts
- **Fixture figures are inputs, not results.** None of them appears in the application, and they differ from the real Phase 2 figures, so a test cannot pass by accident.

## I. Example
```ts
userFixture("admin").permissions.includes("view_audit_log"); // true
```

## J. Maintenance Notes
If the API's role table changes, update `PERMISSIONS` to match.

## K. Related Files
- [server.ts](server.ts.explanation.md): uses these.
