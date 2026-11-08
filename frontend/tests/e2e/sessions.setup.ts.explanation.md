# sessions.setup.ts

Source: [frontend/tests/e2e/sessions.setup.ts](sessions.setup.ts)

## A. File Purpose
The `setup` project: signs in once per main role through the real form and saves each browser state.

## B. Why This File Exists
Later tests start signed in without retyping passwords, which keeps them fast and keeps typed passwords to one place.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `support.ts`.
- **External services / database:** The test API.
- **Depended on by:** Every other project depends on it.

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
For admin, investigator, analyst, demo and colleague: sign in, then save the state to `.e2e/state-<name>.json`.

## G. Input and Output
Output: five Git-ignored state files holding test session cookies.

## H. Important Technical Concepts
- **Separate accounts for disruptive tests:** sign-out, expiry, password change and deactivation use their own seeded accounts, so they never end these saved sessions.

## I. Example
```powershell
npx playwright test --project=setup
```

## J. Maintenance Notes
Add a role here if a spec needs a new saved state.

## K. Related Files
- [support.ts](support.ts.explanation.md): shared helpers.
