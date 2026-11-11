# Phase 5 gate: Firefox reliability investigation

Status: investigation complete, 2026-11-11. The Phase 5 gate stays open. The status-change failure was not reproduced, so one residual risk needs the reviewer's explicit decision (section 5).

This follows the reviewer's decision at the M9 gate: the gate is not accepted while the two first-run Firefox failures are unexplained. The scope was narrow: reproduce the failures under controlled conditions, find causes, and change nothing else. No timeout was raised, and no assertion was removed or relaxed.

## 1. Outcome

| Item | Result |
|---|---|
| Firefox status-change failure | **Not reproduced** in 33 runs, under normal and heavy CPU load. Server, database and rendering causes are excluded by evidence. Two candidates remain that the lost evidence cannot separate. The test now checks each step, so a recurrence would name the failing step. **Residual risk for approval.** |
| Firefox teardown hang | **Reproduced and bounded:** 11 hangs in 3 runs under CPU load, 0 in 30 runs without it. Every test step had passed; Playwright's "Close context" call to Firefox was never answered. The cause lies in Playwright's Firefox build under CPU starvation, not in the application or the test's steps. |
| Found during the investigation | A race in the batch progress test (fixed, below). Stored test sessions expire after 30 minutes, which slow runs exceed (recorded, not changed). One statement in the M9 documents was wrong (corrected). |

## 2. Method

Every run used the real browser-test stack: API `finguard-api-e2e-1` on 127.0.0.1:8011, database `finguard_e2e_test`, and the built frontend on `vite preview`. A temporary Playwright configuration, kept outside the repository and not committed, added three things to the normal one: a trace for failed tests (console, network and DOM snapshots), a JSON report with timings, and Playwright's timestamped browser-process log. After each run a script saved the API container's log and the database's status-change history.

| Run | What | Runs | Result |
|---|---|---|---|
| E1 | The status test alone in Firefox, repeated | 20 | 20 passed |
| E2 | `batches.spec.ts` then `investigations.spec.ts` in Firefox | 5 | Status test passed 5 of 5; the batch progress test failed once |
| E3 | Full order: setup, desktop, tablet, mobile, firefox | 3 | Status test passed 3 of 3; the batch progress test failed once |
| E4 | As E3, machine otherwise idle | 2 | 209 of 209 passed, twice |
| E5 | As E3, with 14 busy-loop processes competing for the CPU | 3 | Status test passed 3 of 3; 3 or 4 teardown hangs per run; later failures from expired sessions (section 4) |
| V1 | After the fixes: both changed tests ×10 in Chromium, Firefox and WebKit | 1 | 65 of 65 passed |

In E2 to E5 the batch tests, including the one that switches the database off mid-job, ran straight before `investigations.spec.ts`. That is the order of both earlier failures.

## 3. Status-change failure

**What was observed.** In the first gate run, "changes status, asks before concluding, and keeps the history" (`investigations.spec.ts`) selected Under review and clicked Update status. For 10 seconds the case badge kept reading New: the locator found the panel and its New badge 23 times. M7's assignment failure was the same symptom, in the same position after the batch tests.

**Evidence that no longer exists.** The browser-test API container was recreated at 12:02 for the rerun, which discarded its log of the failed run. The rerun's global set-up then emptied the test database. The failed run kept no trace, because traces are off in the normal configuration (tests type passwords). So whether the PATCH request was sent in that run cannot be established after the fact.

**What is excluded, and why:**

| Possible cause | Evidence against it |
|---|---|
| Slow or failed API | In the gate rerun, all 87 status and assignment changes were answered within 210 ms. In E1 to E5 the API log's case changes were all answered 200, apart from the refusals the tests ask for (one 409 from the stale-page test, one 422 for an analyst assignee and, in full runs, one 403 for a role without permission, per engine), in identical numbers in every run. The test's own first step (scoring a transaction) and the case's GET had both just succeeded. |
| Change committed late | `investigation_service.update_investigation` commits before the response is sent. The page's reload is a GET after that response. |
| Stale answer overwriting a newer one | `useApiResource` drops any response that is not the latest request's. |
| Failed reload | A failed GET replaces the whole panel with an error message. The failing locator found the panel with its badge 23 times. |
| Panel or form remounted, resetting the choice | The panel is keyed by the case identifier, which did not change. The form sits under the user's permissions, which change only at sign-in, sign-out or session expiry, and each of those replaces the page. |
| Firefox's slow-script watchdog killing the click handler | Playwright's Firefox build disables the watchdog (`dom.max_script_run_time` 0). The "Script terminated by timeout" lines in Firefox's log come from Playwright closing a page while its script runs. A controlled script showed this: a busy click handler was stopped when the page or context closed, and was not stopped by navigation. All 29 such lines in the investigation runs fall within 2 seconds of a Firefox test ending. They are teardown, not a lost click. |
| Test order | 0 failures in 13 runs with the batch tests directly before, including the database-outage test. |
| CPU load | 0 failures in 3 runs under heavy load, where other Firefox problems appeared readily. |

**What remains.** Two explanations fit the failed run and could not be told apart with the lost evidence:
1. the click did not reach the form, so no request was sent; or
2. the request was refused (for example 409, 503), in which case the page would also have shown an error message.

Neither has been seen in 33 runs.

**Change made.** The test now checks the first change in steps, before its original assertions:
- the click must send a PATCH for this case within 10 seconds (the existing `expect` timeout);
- the API must answer 200 with the status Under review;
- the page must then show it (the original assertion).

If it fails again, the failing line says which of the three steps broke. All original assertions are kept, and no timeout was raised. It passed 30 of 30 times in V1 (10 per engine).

## 4. Firefox teardown hang

**What was observed.** At the gate, "the navigation menu opens, works by keyboard, and hides its links when closed" completed its steps, then closing the browser context exceeded the 60-second test limit.

**Reproduction.** None in 30 runs without load (E1 to E4). Under CPU load (E5), 11 hangs in 3 runs, in five different tests: the database-outage batch test, two Model Performance tests and two resilience tests.

**Evidence from the traces (three hangs examined):**
- every test step and assertion had finished;
- Playwright then sent "Close context" to Firefox, and Firefox never answered it, until the test's whole time limit ran out (300, 60 and 60 seconds);
- afterwards Firefox did not exit when asked, and Playwright force-killed it after 30 seconds. This happened after all 11 hangs.

Under the same load, Chromium's browser process also needed force-killing after its 30-second shutdown allowance, 4 times in the 3 loaded runs. That was at worker shutdown, outside any test, so no test failed. Neither engine needed force-killing anywhere in E1 to E4.

**Where the cause lies:**

| Candidate | Finding |
|---|---|
| The test | Excluded: the hang begins after the test's last step, in Playwright's own fixture teardown. |
| The application | Excluded: the page has no `beforeunload`, `unload` or `pagehide` handler, and the script termination seen at close is Firefox's normal behaviour when a page is closed mid-script (controlled script above). |
| Playwright's Firefox driver or Firefox | The hang is inside Playwright's patched Firefox build: the browser-side driver (Juggler) never answers the close. These tests cannot separate Juggler from the browser engine, because Juggler runs inside Firefox. |
| The environment | Contributing: the hang appears readily under CPU starvation and not otherwise. The gate run had no artificial load, and what else was competing for the machine then is not recorded. |

The hang affects test infrastructure only; no request or stored data is involved. Raising the timeout would not help, because the close never completes.

**Expired sessions under load.** Every non-hang failure in E5 began 30.0 minutes or more after the setup project signed in. The stored sessions last 30 minutes (`access_token_minutes`), and the loaded runs took 37 to 46 minutes. The pages showed Sign in, and API calls were refused. This is a property of the test design (sign in once, reuse the session), not of Firefox. It was not changed. A full run on a normal machine takes about 17 minutes.

## 5. Residual risk for the reviewer's decision

**Status change in Firefox, unexplained single failure.** It was seen once at the gate and once in M7 (assignment), and not since in 33 runs. Its cause is not identified. The release-gate condition allows an evidence-backed explanation only with an explicitly approved residual risk. This record does not approve it. The decision is the reviewer's:
- accept the residual risk, with the step-by-step test in place to identify the cause if it recurs; or
- keep the gate open and require more runs.

**Teardown hang.** It is bounded to Playwright's Firefox build under CPU starvation. It is not an application defect. It is recorded as a known limitation of the browser tests.

## 6. Batch progress test race (fixed)

"shows processing progress for a larger file until it completes" failed in 2 of 13 Firefox runs (E2 and E3) with `expect(seen[seen.length - 1]).toBe(100)` receiving 95.

The traces showed the API going from Processing at 95% straight to Completed at 100%. The API never reported Completed below 100%. The poll read the bar's value and then its label in two separate browser calls. A re-render between them gave a value from one answer and a label from the next.

The two are now read in one `evaluate` call, from one render. All assertions are unchanged. Afterwards it passed 30 of 30 times in V1 (10 per engine).

## 7. Corrections to the M9 documents

TESTING_GUIDE.md said Firefox's log showed "its slow-script watchdog stopping the page's start-up script". That is wrong. The watchdog is disabled, and the lines come from Playwright closing pages (section 3). Corrected.

## 8. Final verification

| Check | Result |
|---|---|
| Both changed tests ×10 per engine, with setup (V1) | 65 passed, 0 failed |
| Complete browser suite, all seven projects | 311 passed, 0 failed, 0 skipped (setup 5, desktop 83, tablet 19, mobile 19, firefox 83, webkit 83, webkit-mobile 19) |
| Type check (covers the tests) | Passed |
| Explanation checker | 235 files, 0 problems |
| Secret scan | 0 findings |
| Model hash | `69813c176b02d035f550e80f0f694f44bb9fec8a31222a25de189525a91ad40c`, unchanged |
| Threshold | `0.02841914258897305`, unchanged |
| `data/`, `artifacts/`, `experiments/` | No differences from M9 (`80d228c`) |

One complete run is not counted: it was started from a shell without Docker on its PATH, and the 15 container-control tests failed with `spawnSync docker ENOENT`. It is recorded in [TESTING_GUIDE.md](../../TESTING_GUIDE.md#phase-5-firefox-investigation-follow-up-2026-11-11).

Traces and logs from the investigation stay outside the repository, because traces can contain request headers. Nothing from them is quoted here except status codes, timings and page text.
