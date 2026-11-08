# responsive.spec.ts

Source: [frontend/tests/e2e/responsive.spec.ts](responsive.spec.ts)

## A. File Purpose
Checks layout and accessibility at desktop (1440 x 900), tablet (768 x 1024) and mobile (390 x 844): overflow, automated WCAG 2.2 A/AA checks, CSP errors, the top bar, the navigation menu, keyboard use, focus, dialogs and touch targets.

## B. Why This File Exists
Authorisation decision 4 and the M7 brief require desktop, tablet, mobile and accessibility coverage, and fixing genuine issues rather than suppressing them.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `support.ts`.
- **External services / database:** The browser-test API on 127.0.0.1:8011 and the finguard_test database, through the preview server on 127.0.0.1:4173.
- **Depended on by:** none; run by `npm run test:e2e`.

## D. Every Function Explained

### `narrow`
True for the tablet and mobile projects.

### `settle`
Waits for the page heading, network quiet and no loading state.

### `expectNoAxeViolations`
Runs axe with the WCAG 2.0, 2.1 and 2.2 A and AA tags and fails with a readable list. No rule is disabled.

### `expectNoHorizontalScroll`
Fails on sideways scrolling, and on a layout viewport wider than the device, which is how an overflowing select showed on phones.

### `screenshot`
Saves a full-page screenshot to `.e2e/screenshots/<project>-<name>.png`.

### `expectTouchTargets`
Fails if any visible control is smaller than 24 x 24 CSS pixels (WCAG 2.5.8), except inline text links.

### `textLines`
A local value, not a function: counts the lines a piece of text occupies, using a Range, because a flex item reports one box even when its text wraps.

## E. Classes Explained
None.

## F. Execution Flow
Runs in all three projects as the administrator, who can open every page, plus the sign-in page signed out.

## G. Input and Output
| Test | Proves (each viewport) |
|---|---|
| <page>: fits, has no automated WCAG violations and no CSP errors (ten pages) | No overflow, no axe violations, target sizes, no console or CSP errors. |
| an open investigation and its confirmation dialog fit and pass the checks | The panel and dialog. |
| a chart switches to its table by keyboard | Enter toggles, focus stays. |
| the top bar stays on one line and inside the screen | FinGuard AI, the role and Sign out each on one line. |
| the navigation menu opens, works by keyboard, and hides its links when closed | Closed links never take focus; Escape closes and returns focus; a link closes the menu. Desktop: collapse and expand. |
| the skip link and focus indicator work from the keyboard | Skip link first, focus moves to main, visible focus ring. |
| a confirmation dialog keeps focus inside and returns it when closed | Focus trap and return. |
| sign-in page: fits, has no automated WCAG violations, and shows field errors accessibly | The signed-out page and its error state. |

## H. Important Technical Concepts
- **Data first:** `beforeAll` creates records, so tables, badges and row buttons are always present to check.
- **Located by id:** the closed menu is absent from the accessibility tree, so it is found by `#main-navigation`.
- **Defects this found:** see the Phase 4 report; each fix has a unit or browser regression test.

## I. Example
```powershell
npm run test:e2e -- tests/e2e/responsive.spec.ts --project=setup --project=desktop
```

## J. Maintenance Notes
Fix violations in the code; never add `disableRules` or exclusions without recording a justified exception in TESTING_GUIDE.md.

## K. Related Files
- [support.ts](support.ts.explanation.md): shared helpers.
- [AppLayout.tsx](../../src/layouts/AppLayout.tsx.explanation.md): the frame.
