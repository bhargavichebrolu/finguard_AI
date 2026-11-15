# Screen-reader checklist (Phase 5 M6)

**Status: UNTESTED.** Screen-reader behaviour has not been verified. Automated tests check the accessibility tree that screen readers receive (`frontend/tests/e2e/accessibility-tree.spec.ts`), axe rules and keyboard use, but none of them can judge what is spoken or whether it makes sense. This page becomes evidence only when a person runs it and records the results below. Until then no screen-reader compatibility is claimed.

## Set-up

- **Narrator** (built into Windows): start and stop with `Ctrl` + `Windows` + `Enter`. Use Microsoft Edge.
- **NVDA** (free, from nvaccess.org): start with `Ctrl` + `Alt` + `N`. Use Firefox or Chrome.
- Start the application locally (`ENVIRONMENT_SETUP.md`) and sign in with a test account. Use a fresh browser window. Do not use a real password you use elsewhere.
- Useful keys: next heading `H`, next landmark `D` (NVDA) or `Caps Lock` + `Right` with landmark view (Narrator), next form field `F`, tables `T`, read from here `Insert` + `Down` (NVDA) or `Caps Lock` + `R` (Narrator). Turn off any mouse use.

## Steps

For each step, record **Pass**, **Fail** (with what was heard) or **Not run**.

| # | Do | Expect to hear | Narrator | NVDA |
|---|---|---|---|---|
| 1 | Open the sign-in page | "Sign in, heading level 1"; the research and demonstration notice | Not run | Not run |
| 2 | Tab through the form | "Email, edit", "Password, edit, protected", "Sign in, button, unavailable" until both are filled | Not run | Not run |
| 3 | Submit a wrong password | "Incorrect email or password." spoken without moving focus (alert) | Not run | Not run |
| 4 | Sign in; press Tab once | "Skip to content, link"; Enter moves to the main content | Not run | Not run |
| 5 | List landmarks | banner, navigation "Main navigation", main, complementary "How to read model scores" | Not run | Not run |
| 6 | Read the disclosure | That scores are not calibrated and not the chance a transaction is fraud, then the measured false positive rate and recall | Not run | Not run |
| 7 | Move through the navigation | Ten links in PRD order; the current page is identified | Not run | Not run |
| 8 | Transaction Analysis: submit the empty form | Each field is "invalid" and its error message is read with it | Not run | Not run |
| 9 | Score a valid transaction | The result: decision, risk, "Model score (uncalibrated)" and the number, read as values not percentages | Not run | Not run |
| 10 | Dashboard: open a chart's table view | "Show table, toggle button, not pressed", then "pressed"; the table is read with column headers | Not run | Not run |
| 11 | Explorer: move through the results table | Row and column headers announced with each cell | Not run | Not run |
| 12 | Investigation Centre: open a case and choose Closed | A dialog is announced with its title and message; focus is on Cancel; Tab stays within the dialog; Escape returns focus to Update status | Not run | Not run |
| 13 | CSV Batch Analysis: upload a file | The upload result; whether progress changes are announced (they are not in a live region, so silence here is expected and should be noted) | Not run | Not run |
| 14 | Narrow the window below 900 pixels | "Open navigation, button, collapsed"; after opening, the links; Escape closes and returns focus | Not run | Not run |
| 15 | Settings: account table (administrator) | Each row's role select is named "Role for <email>" | Not run | Not run |

## Results

| Date | Tester | Screen reader and version | Browser and version | Steps passed | Problems found |
|---|---|---|---|---|---|
| — | — | — | — | — | Not yet run |

Record problems as issues with the step number and exactly what was spoken. A fix needs a regression test where one is possible (for example an accessibility-tree assertion).
