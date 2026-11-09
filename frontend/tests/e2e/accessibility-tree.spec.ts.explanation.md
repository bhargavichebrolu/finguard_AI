# accessibility-tree.spec.ts

Source: [frontend/tests/e2e/accessibility-tree.spec.ts](accessibility-tree.spec.ts)

## A. File Purpose
Checks the accessibility tree of key screens (what a screen reader is given): landmarks, headings, accessible names, roles and states, compared with an expected outline.

## B. Why This File Exists
The Phase 5 approval keeps screen-reader behaviour untested until the owner runs the manual checklist. Short of that, the strongest automated evidence is the tree assistive technology reads. axe checks rules; this checks that the structure is the intended one, for example the ten navigation links in PRD order and a named modal dialog.

## C. Dependencies
- **Libraries:** Playwright Test (`toMatchAriaSnapshot`).
- **Internal modules:** `support.ts` (`NO_SESSION`, `statePath`).
- **External services / database:** The test API and database, through the preview server.
- **Depended on by:** `npm run test:e2e` (the desktop, Firefox and WebKit projects).

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
Each test opens a page, waits for it, and compares a region's accessibility tree with a YAML outline. Interactions (a failed sign-in, an empty submission, opening a dialog, switching to a table) are followed by a second comparison or explicit state assertions.

## G. Input and Output
| Test | Proves |
|---|---|
| the sign-in page names its heading, fields, button and errors | Level 1 heading, labelled fields, a disabled button until filled, and the error as an alert. |
| the frame has a skip link, banner, navigation in order, main and the score disclosure | Landmarks and the ten links in PRD order; the score disclosure is a named complementary region. |
| the scoring form exposes names, the disabled destination and invalid fields | Every control is named; an empty submission marks Amount invalid and describes it with the error. |
| a confirmation dialog is a named modal with its message and both choices | Named `dialog`, `aria-modal`, its message as the description, Cancel and the action. |
| charts are hidden from assistive technology and offer a named table instead | The SVG is not in the tree; the toggle is pressed; the table is named and has headers. |

## H. Important Technical Concepts
- **Partial matching:** an outline lists what must be present, in order; other nodes may sit between. Order is enforced: swapping two navigation links in the outline made the test fail (checked when it was written).
- **Not a screen-reader test:** it says what is exposed, not what is spoken or whether it is understandable. `docs/accessibility/screen-reader-checklist.md` covers that and is marked UNTESTED.

## I. Example
```powershell
npm run test:e2e -- tests/e2e/accessibility-tree.spec.ts --project=setup --project=desktop
```

## J. Maintenance Notes
When a screen's structure changes on purpose, update its outline in the same commit. Do not loosen an outline to a regular expression or drop a node to make a run pass.

## K. Related Files
- [responsive.spec.ts](responsive.spec.ts.explanation.md): axe, keyboard and layout checks.
- [screen-reader-checklist.md](../../../docs/accessibility/screen-reader-checklist.md): the manual test.
