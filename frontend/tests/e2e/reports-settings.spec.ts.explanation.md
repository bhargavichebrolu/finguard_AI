# reports-settings.spec.ts

Source: [frontend/tests/e2e/reports-settings.spec.ts](reports-settings.spec.ts)

## A. File Purpose
Tests the four report downloads and Settings: the high risk boundary, password change, account creation, role change and deactivation.

## B. Why This File Exists
PRD 6.9 and 6.10, and the brief's Reports and Settings requirements, including that administrators cannot deactivate their own account.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `support.ts`.
- **External services / database:** The browser-test API on 127.0.0.1:8011 and the finguard_test database, through the preview server on 127.0.0.1:4173.
- **Depended on by:** none; run by `npm run test:e2e`.

## D. Every Function Explained

### `downloadReport`
Clicks a report button and returns the file name and lines.

### `signedInAs`
Opens a new signed-out context and starts a session for the given credentials.

### `stored`
A local value, not a function: the count of stored transactions, compared with the flag summary.

### `settings`
A local value, not a function: the settings before the boundary test, restored afterwards.

### `audit`
A local value, not a function: recent audit entries.

### `after`
A local value, not a function: the new account's details after its role changed.

### `me`
A local value, not a function: the signed-in administrator.

## E. Classes Explained
None.

## F. Execution Flow
Each test signs in through a saved state and works through the real interface and API.

## G. Input and Output
| Test | Proves |
|---|---|
| downloads all four reports with their saved contents | File names and headers; no labels in predictions; flag summary totals equal stored records; model evaluation test recall equals `model_v1_metrics.json`. |
| demo users cannot export | Page and API refuse. |
| an administrator changes it after confirming, and new predictions use it | Validation, Cancel, confirmation, persistence, a new prediction banded Medium under 0.5 with the flag and frozen threshold unchanged, audit entry; the old value is restored. |
| signs the user out everywhere, and only the new password then works | Password change. |
| creates an account and changes its role | The new account can sign in; a role change applies to its open session. |
| deactivates another account after confirming, ending its live session | Confirmation, and the live session and sign-in refused. |
| an administrator cannot deactivate their own account, in the interface or the API | Disabled button and 422 from the API. |

## H. Important Technical Concepts
- **Restoring state:** the boundary test restores the original value in `finally`, so later tests are unaffected.

## I. Example
```powershell
npm run test:e2e -- tests/e2e/reports-settings.spec.ts --project=setup --project=desktop
```

## J. Maintenance Notes
The password and deactivation tests consume their seeded accounts; the next run's seed recreates them.

## K. Related Files
- [support.ts](support.ts.explanation.md): shared helpers.
- [auth_service.py](../../../backend/app/services/auth_service.py.explanation.md): account rules.
