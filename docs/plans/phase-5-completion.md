# Phase 5 completion: integration hardening, quality assurance and reliability

Status: **accepted on 2026-11-13 with its documented residual risks**, after the Firefox reliability investigation ([phase-5-firefox-investigation.md](phase-5-firefox-investigation.md), follow-up commit `79b2947`). All nine milestones are on branch `phase-5-hardening`, which is not merged into `main` and not pushed. Phase 6 continues on the same branch ([phase-6-completion.md](phase-6-completion.md)).

**Open item for the reviewer:** the first browser run at the gate had two Firefox failures.
- **The teardown hang** is now reproduced and bounded. It is a hang in Playwright's Firefox build under CPU starvation, not an application defect.
- **The status-change failure** was not reproduced in 33 runs. Its residual risk needs the reviewer's explicit decision.

Plan: [phase-5-plan.md](phase-5-plan.md), approved 2026-11-08. Decisions: [ADR 0005](../decisions/0005-phase-5-decisions.md).

## Milestones

| Milestone | Scope | Commit |
|---|---|---|
| M1 | Test isolation (`finguard_e2e_test`), clean-clone check, images pinned by digest | `373a196` |
| M2 | Measured performance baseline; dashboard summary and CSV export fixed | `86a1dfd` |
| M3 | Rate limits in PostgreSQL within the latency budget; worker count; concurrent start-up | `395cef4` |
| M4 | Batch processing as a recoverable, multi-process queue | `7e48938` |
| M5 | Production security review, HTTPS stack, cookie prefixes, secret scan, audits, retention | `019dad9` |
| M6 | Firefox and WebKit, accessibility tree, screen-reader checklist | `f592de5` |
| M7 | Integration error handling | `5afdd37` |
| M8 | CI workflow with a fixed expected-skip list | `1621449` |
| M9 | Documentation review, ADR 0005, this record | The commit that adds this file |

## Approval decisions and conditions

| Decision or condition | Evidence |
|---|---|
| 1. PostgreSQL batch queue, workers inside API processes | ADR 0005 D1; `test_batch_queue.py`, `test_multiprocess.py`, `test_failures.py`, `batches.spec.ts` |
| 2. PostgreSQL rate limits within the M2 budget | Budget fixed before M3 code ([baseline](../performance/phase-5-baseline.md)). The sliding-window design was rejected (3 of 4 checks over budget); the fixed window was accepted (4 of 4 within) ([M3 record](../performance/phase-5-m3-rate-limits-and-workers.md)). |
| 3. Caddy for HTTPS testing | `docker/caddy/Caddyfile`, `scripts/prodlike_stack.py`, `frontend/tests/prodlike/production.spec.ts` |
| 4. `__Host-` and `__Secure-` prefixes in production | `test_sessions.py::test_secure_cookies_carry_browser_enforced_prefixes`; the HTTPS sign-in test |
| 5. Firefox, WebKit, `pip-audit` | `frontend/playwright.config.ts` projects; `pip-audit` in the `dev` group |
| 6. CI with a fixed skip list; unexpected skips fail | `.github/workflows/ci.yml`, `.github/expected-tests.json`, `scripts/check_test_run.py`; demonstrated failing on a run without a database |
| 7. Retention command: 7 days for sessions, 365 days for audit records | `python -m app.commands.retention`; `test_retention.py` |
| 8. Narrator/NVDA checklist, untested until the owner runs it | [screen-reader-checklist.md](../accessibility/screen-reader-checklist.md), status **UNTESTED** |
| Batch: SKIP LOCKED, ownership, leases, heartbeats, abandoned-job recovery | `claim_next_job`, the lease renewed per chunk, `fail_exhausted_jobs`; `test_simultaneous_claims_never_take_the_same_job`, `test_a_worker_that_lost_its_lease_stores_nothing` |
| Batch: persisted progress, idempotent chunks, no duplicate predictions | `test_a_crash_mid_chunk_resumes_after_the_last_commit_without_duplicates` (rows without identifiers, so a repeat would show) |
| Batch: storage reachable from separate containers | Bytes are in `batch_uploads`; `test_a_killed_process_s_batch_is_finished_by_another_process` uses a second process with a different upload folder |
| Batch: unsafe start-up logic removed | Start-up touches no jobs; `test_two_processes_share_the_queue_and_store_every_row_once` |
| Batch: crashes, restarts, concurrent workers | Real killed process (`test_multiprocess.py`); API container restarted mid-job, and database turned off mid-job (`batches.spec.ts`) |
| Rate limits: correct across processes and restarts | `test_failed_sign_ins_are_counted_across_processes_and_restarts`; the old memory store's failure is shown by `test_the_memory_store_lets_each_process_allow_the_full_limit` |
| HTTPS: full path, cookie flags, CSRF, CORS, forwarding, trusted proxies | 6 HTTPS browser tests; security findings S1–S6 |
| CI: report that real-model inference is not verified | `expected-tests.json` notes, printed in every job summary |
| CI: no claim of a GitHub pass | Stated in `ci.yml.explanation.md`, TESTING_GUIDE.md and here |
| Retention: dry run and apply, counts and cutoffs, boundaries | `test_retention.py`: a dry run deletes nothing; apply deletes exactly what the dry run reported; rows either side of the 7-day, 365-day and 1-day cutoffs |
| Frozen artefacts preserved; no retraining; no test-set analysis | Hash and directory checks below; the one test that rereads the test partition stays deselected |
| Explanation documents and `PROJECT_CONNECTIONS.md` | Checker result below |
| No push, no deployment, no image shrink | Nothing pushed; finding F12 left for Phase 6 |

## Results at the gate

| Suite | Passed | Failed | Skipped | Deselected |
|---|---|---|---|---|
| Backend, full, with the model | 778 | 0 | 0 | 1 (rereads the test partition) |
| Frontend unit and component (Vitest) | 111 | 0 | 0 | 0 |
| Browser, first gate run (all seven projects) | 309 | **2, both Firefox, unexplained** | 0 | 0 |
| Browser, full rerun (all seven projects) | 311 | 0 | 0 | 0 |
| HTTPS production-like | 6 | 0 | 0 | 0 |
| CI rehearsal, fresh clone: backend | 480 | 0 | 298, exactly the expected list | 1 |
| CI rehearsal, fresh clone: frontend | 111 | 0 | 0 | 0 |

Browser rerun by project: setup 5, desktop 83, tablet 19, mobile 19, firefox 83, webkit 83, webkit-mobile 19.

Other checks, all passed on the CI rehearsal of the final tree (all 19 workflow steps):
- `ruff check`, and `ruff format --check` (167 files).
- Explanation checker: 235 files, 0 problems.
- `export_openapi.py --check` and `export_model_report.py --check`.
- `scan_secrets.py`: 0 findings, 0 secret files.
- `pip-audit` and `npm audit`: 0 known vulnerabilities.
- Type check and production build.

The CI workflow itself has **not** run on GitHub.

**The two first-run browser failures:**
- "changes status, asks before concluding, and keeps the history": a status change did not show within 10 seconds. This is the same symptom as M7's assignment failure, and both came after the batch tests.
- "the navigation menu opens, works by keyboard, and hides its links when closed": closing the browser context hung in Firefox.

At M9 neither reproduced, and no test or assertion was changed. In the rerun the API's request log was kept: all 87 status and assignment changes were answered within 210 ms. Details are in [TESTING_GUIDE.md](../../TESTING_GUIDE.md#phase-5-gate-results-m9-2026-11-11).

The follow-up investigation ([phase-5-firefox-investigation.md](phase-5-firefox-investigation.md)) changed two tests, keeping every original assertion.
- The status test now checks the request and the API's answer before the badge.
- A race in the batch progress test was fixed: it was found during the investigation, and it had failed in 2 of 13 Firefox runs.

## Multi-process and batch-recovery evidence

| Test | What it shows |
|---|---|
| `test_failed_sign_ins_are_counted_across_processes_and_restarts` | Five failed sign-ins split across two real API processes hit the limit in both, and a restart does not reset it |
| `test_processes_starting_together_register_the_model_once` | Four processes starting together register the model once (before the advisory lock, two of three runs failed) |
| `test_a_killed_process_s_batch_is_finished_by_another_process` | A real API process killed mid-batch; another process finishes all 6,000 rows once, on attempt 2 |
| `test_two_processes_share_the_queue_and_store_every_row_once` | Two processes share four jobs with no row stored twice |
| `test_several_workers_on_several_jobs_store_every_row_once`, `test_simultaneous_claims_never_take_the_same_job` | Concurrent workers never share a job |
| `test_failures.py` (M7) | A lost database connection mid-batch resumes with 450 rows and 450 predictions; recovery through the lease while the database stays down |
| `batches.spec.ts` | API container restarted mid-job: the page shows "Resuming after an interruption" and 20,000 rows finish. Database turned off mid-job: the job resumes at attempt 2 and stores 20,000 rows once. A file submitted twice stores each identified row once. |

## Performance measurements

All figures are from saved run files in [docs/performance/](../performance/phase-5-baseline.md). They were measured on this Windows machine in Docker Desktop, with synthetic inputs, and say nothing about any hosting platform.

| Measure | Result |
|---|---|
| Prediction latency, one process (M2) | Sequential p50 37.61 ms and p95 44.95 ms; 8 concurrent p50 297.93 ms, 26.6 requests per second |
| Dashboard summary at 500,000 predictions | p50 862.19 ms before, 433.94 ms after M2's grouped query |
| CSV export, 500,000 rows | p50 109.5 s before, 10.4 s after (same 98,869,998 bytes); API memory after export 495.6 MiB before, 169.7 MiB after |
| PostgreSQL rate limits (M3) | Fixed window within budget on all four checks; sliding window rejected |
| Workers (M3) | 1: 40–42 requests per second concurrent, 166.5 MiB idle. 2: 74–75 per second, 345.4 MiB. 4: 46–49 per second, 654.5 MiB. The default stays at 1. |
| Batch throughput after M4 | 1,629.4 rows per second at 50,000 rows |
| Deep explorer offsets | Last page at 500,000 rows: p50 2664.13 ms (`OFFSET`); recorded as a limitation |

## HTTPS and security verification

[docs/security/phase-5-review.md](../security/phase-5-review.md) records 15 findings:

| Status | Findings |
|---|---|
| Fixed | S2 cookie prefixes, S8 scanner rule, S10 retention |
| Verified | S1 HTTPS path, S3 CSRF and origin, S4 CORS, S5 forwarded headers, S6 headers, S11 configuration separation |
| Clean | S7 secrets in history, S9 dependencies (rechecked at the gate below) |
| Recorded for review | S12 upload bytes in the database (PRD 9.2 interpretation, ADR 0005) |
| Open for Phase 6 | S13 `/docs` in production, S14 sign-in limit behind an unlisted proxy, S15 public certificate |

There was no penetration test and no external review.

## Cross-browser results

Every browser test runs in Playwright's Chromium, Firefox 159 and WebKit 27.2 builds. Per-project counts at the gate are under Results above.

WebKit here is the engine on Windows, not Safari on macOS or iOS, and `webkit-mobile` is a narrow window, not an iPhone. **Safari itself has not been tested.** SameSite=Strict is checked on the `Set-Cookie` header in every engine. WebKit's stored cookie reports `SameSite=None`, so **whether WebKit enforces Strict is not established by these tests.**

## Screen-reader checklist

**UNTESTED.** The Narrator and NVDA protocol is written, but no person has run it, so no screen-reader compatibility is claimed. The automated evidence is accessibility-tree, axe and keyboard tests. These cannot judge spoken output.

## Frozen artefacts

| Check | Result |
|---|---|
| `artifacts/models/fraud_detector_v1/model.joblib` SHA-256 | `69813c176b02d035f550e80f0f694f44bb9fec8a31222a25de189525a91ad40c`, the pinned value (unchanged since Phase 2) |
| Tracked files under `data/`, `artifacts/`, `experiments/` | No differences in M9. In all of Phase 5, one file changed: in M1, `artifacts/metadata/model_v1_report.json`, a report derived in Phase 4. Only its `source_files` section changed: six hashes became hashes of content with line endings normalised. Every value in the report, and its sources, are identical (M1 commit `373a196`). No dataset, model file, experiment result, metric or threshold changed. |
| Threshold | `FROZEN_THRESHOLD = 0.02841914258897305` in `backend/app/core/frozen_model.py`, unchanged |
| Test partition | Not read: `test_test_results_can_be_recalculated_from_the_saved_model` deselected in every run |
| Retraining | None |

## Known limitations

See the Phase 5 entry in [CHANGELOG.md](../../CHANGELOG.md) and [SECURITY.md](../../SECURITY.md#known-limitations).

## Git

- **Branch:** `phase-5-hardening`, ahead of `main` (`5c392a5`) by the approved plan (`dac5bd5`), M1 to M9 (M9 is `80d228c`), and the Firefox investigation follow-up.
- **HEAD:** the follow-up commit, on top of `80d228c`. Its hash and the working-tree status after committing are given in the report, because a commit cannot contain its own hash.
- **Not pushed, and not merged into `main`.**
