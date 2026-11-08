# source-rules.test.ts

Source: [frontend/tests/unit/source-rules.test.ts](source-rules.test.ts)

## A. File Purpose
Scans the application's source for forbidden wording, hardcoded Phase 2 figures, browser storage, raw HTML and inline styles, and checks the generated API types are current.

## B. Why This File Exists
These rules from the authorisation and PRD apply to every file. A scan catches a violation in a file nobody thought to test.

## C. Dependencies
- **Libraries:** Vitest, Node `fs` and `path`, `openapi-typescript`.
- **Internal modules:** none. It reads `src/` and `openapi.json`.
- **External services / database:** none.
- **Depended on by:** none; run by Vitest.

## D. Every Function Explained

### `sourceFiles`
Lists every `.ts` and `.tsx` file under `src`, except the generated types.

### `body`
Nested. Trims the generated file's banner comment, so only the type definitions are compared.

## E. Classes Explained
None.

## F. Execution Flow
Read files once, then apply each rule.

## G. Input and Output
| Test | Proves |
|---|---|
| finds the application's source files | The scan is not empty, so it cannot pass vacuously. |
| never calls a score a probability or a flag a fraud finding | Wording rule. |
| contains none of the saved Phase 2 figures, which must come from the API | No hardcoded statistics (PRD 7.5). |
| never touches browser storage, where tokens must not live | Authorisation decision 1. |
| never injects raw HTML | No `dangerouslySetInnerHTML`. |
| uses no inline style attributes, which the Content Security Policy forbids | CSP compatibility. |
| has generated API types that match frontend/openapi.json | The types are current. |

## H. Important Technical Concepts
- **The figure list includes the frozen threshold's digits,** so even the threshold must come from the API.
- **Comments count:** an earlier comment naming `localStorage` tripped the storage rule, so it was reworded, and the rule was kept strict.

## I. Example
```powershell
npm test -- source-rules
```

## J. Maintenance Notes
Add any new saved figure that pages display to the figure list.

## K. Related Files
- [format.ts](../../src/utils/format.ts.explanation.md): score formatting.
- [export_openapi.py](../../../scripts/export_openapi.py.explanation.md): the schema.
