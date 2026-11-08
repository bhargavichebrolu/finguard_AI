# roles.spec.ts

Source: [frontend/tests/e2e/roles.spec.ts](roles.spec.ts)

## A. File Purpose
Checks each role's navigation and controls, and that the API refuses every restricted action on its own.

## B. Why This File Exists
Authorisation decision 2 and PRD 7.4 require role-based access. The API, not the interface, is the control, so each refusal is checked by calling the API directly.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `support.ts`.
- **External services / database:** The browser-test API on 127.0.0.1:8011 and the finguard_e2e_test database, through the preview server on 127.0.0.1:4173.
- **Depended on by:** none; run by `npm run test:e2e`.

## D. Every Function Explained

### `navigationLabels`
Returns the text of every link in the main navigation, in order.

## E. Classes Explained
None.

## F. Execution Flow
Each test signs in through a saved state and works through the real interface and API.

## G. Input and Output
| Test | Proves |
|---|---|
| navigation lists exactly the permitted pages, in PRD order (four roles) | Demo lacks Investigation Centre and Reports; others see all ten. |
| demo: cannot open restricted pages by address | The not-available page. |
| demo: is refused by the API whatever the interface shows | 403 for investigations, exports, settings, users, audit log. |
| demo records are kept apart from other users' records | A demo prediction is invisible to an analyst. |
| analyst: can view but not change investigations, settings or accounts | Read-only notice, no controls, and 403s for each change. |
| investigator: can work investigations but not change settings or accounts | 200 for case work, 403 for administration. |
| administrator: can open account management and the audit log | 200s. |

## H. Important Technical Concepts
- **Expected lists are written out,** not derived from the code, so a change to permissions is a visible test change.

## I. Example
```powershell
npm run test:e2e -- tests/e2e/roles.spec.ts --project=setup --project=desktop
```

## J. Maintenance Notes
Update `EXPECTED_NAVIGATION` only with the permission table in `permissions.py`.

## K. Related Files
- [support.ts](support.ts.explanation.md): shared helpers.
- [permissions.py](../../../backend/app/security/permissions.py.explanation.md): the role table.
