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
