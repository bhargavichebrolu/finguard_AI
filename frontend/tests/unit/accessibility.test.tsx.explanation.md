# accessibility.test.tsx

Source: [frontend/tests/unit/accessibility.test.tsx](accessibility.test.tsx)

## A. File Purpose
Regression tests for the accessibility defects the browser tests found in components.

## B. Why This File Exists
Each fix needs a fast test that fails without it. These failed against the previous code and pass now.

## C. Dependencies
- **Libraries:** Vitest, Testing Library, `user-event`.
- **Internal modules:** `feedback.tsx`, `DataTable.tsx`, `render.tsx`, `server.ts`.
- **External services / database:** none.
- **Depended on by:** none; run by Vitest.

## D. Every Function Explained

### `DialogHarness`
A test component with an opener button, an outside button and a `ConfirmDialog`. The outside button re-renders the harness, as real pages do.

## E. Classes Explained
None.

## F. Execution Flow
Render, act with the keyboard, check focus.

## G. Input and Output
| Test | Proves |
|---|---|
| is named and described, and starts on Cancel | `aria-labelledby`, `aria-describedby`, `aria-modal`, initial focus. |
| keeps Tab and Shift+Tab inside the dialog | Focus trap. |
| returns focus to the control that opened it, after Escape or a choice | Focus return. |
| is a named group that keyboard users can focus to scroll | `TableScroll`. |
| wraps every DataTable | DataTable uses it. |
| closes the menu with Escape and returns focus to the menu button | Mobile menu. |
| keeps Sign out as the button's name when the label is hidden visually | Accessible name on phones. |

## H. Important Technical Concepts
- **Layout fixes are tested in the browser:** jsdom does not lay out pages, so overflow, hidden menus and target sizes are covered by `responsive.spec.ts`.

## I. Example
```powershell
npm test -- accessibility
```

## J. Maintenance Notes
Add a test here for each future component accessibility fix.

## K. Related Files
- [feedback.tsx](../../src/components/feedback.tsx.explanation.md): the dialog.
- [responsive.spec.ts](../e2e/responsive.spec.ts.explanation.md): browser checks.
