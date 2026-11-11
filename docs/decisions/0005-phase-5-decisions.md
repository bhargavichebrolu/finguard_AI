# ADR 0005: Phase 5 decisions

Status: accepted for Phase 5, subject to review at the phase gate. It records what was built for the decisions approved on 2026-11-08 in [docs/plans/phase-5-plan.md](../plans/phase-5-plan.md) (D1–D6), and the further decisions the milestones needed. Measurements are in [docs/performance/](../performance/phase-5-baseline.md); security findings are in [docs/security/phase-5-review.md](../security/phase-5-review.md).

## D1. Batch processing: a PostgreSQL queue with a worker in each API process (M4)
Approved option A. It replaces ADR 0003 section 10, where FastAPI background tasks read a local temporary file and start-up failed every unfinished job.

| Part | Implementation |
|---|---|
| Upload storage | After every upload check passes, the bytes go into `batch_uploads` (migration `0004`), so any container can process them. They are deleted when the job completes, fails or runs out of attempts. |
| Claiming | Each API process runs one worker thread. Every 2 seconds (`BATCH_POLL_SECONDS`) it claims the oldest waiting job, or one whose lease expired, with `SELECT … FOR UPDATE SKIP LOCKED`. |
| Leases | `lease_expires_at` uses database time. It is set for 60 seconds (`BATCH_LEASE_SECONDS`) and renewed after each chunk. A worker that has lost its lease stores nothing. |
| Progress | Each 1,000-row chunk commits its predictions and `processed_records` in one transaction, under the job's row lock. A resumed job starts after the last committed chunk, and identifiers are unique, so no row is stored twice. |
| Attempts | At most 3 (`BATCH_MAX_ATTEMPTS`). After that the job fails, its stored rows are kept, and its bytes are dropped. The interface shows "Resuming after an interruption" while a job runs again. |
| Shutdown and start-up | A stopping process gives its job back at once. Start-up no longer touches jobs at all; it only removes temporary upload files older than an hour. |
| Lost database (M7) | A connection error gives the job back instead of failing it. If the database is still down, the lease expires and any worker resumes the job. Other errors still fail it. |

**PRD 9.2 interpretation.** The PRD says large uploads should not be stored as unbounded raw blobs, and asks for controlled temporary storage. The stored bytes are bounded (10 MB and 50,000 rows, checked before storage) and temporary, so this was judged to meet that rule. It is recorded here for the reviewer (security finding S12).

## D2. Rate limits shared across processes (M3)
Approved option A, on condition that the prediction path stayed within the latency budget set in M2.

- **First design rejected.** A sliding window behind an advisory lock was over budget on three of four checks (for example, sequential p50 overhead was 3.08 ms against 2.36 ms allowed).
- **Second design accepted.** A fixed one-minute window, counted in `rate_limit_windows` with one autocommit `INSERT … ON CONFLICT`, was within budget on all four checks. It is used for predictions and uploads.
- **Failed sign-ins** keep a sliding window in `rate_limit_events`, because a fixed window could let up to twice the limit through across a minute boundary.

Production refuses the per-process memory store. This replaces ADR 0003 section 11, where limits were in memory and reset on restart.

## D3. Process count
`WEB_CONCURRENCY` sets Uvicorn's worker count, and the default stays at 1. Measured results:

| Workers | Concurrent p50 | Memory |
|---|---|---|
| 1 | 187.12 ms | 166.5 MiB |
| 2 | 94.56 ms | 345.4 MiB |
| 4 | 177.77 ms | 654.5 MiB |

Four workers were slower than two, most likely because model scoring in every worker competes for the same CPU cores. One worker leaves room in a 512 MB container; two are recommended where at least 1 GB is available. With D1 and D2, more than one process is correct, which tests with two real processes demonstrate.

## D4. Same-origin production shape and the HTTPS stack (M5)
ADR 0004's single origin is kept. Compose profile `prodlike` runs Caddy (`caddy:2-alpine`, pinned by digest) in front of the built frontend and an API with `APP_ENV=production`, over HTTPS from Caddy's local authority. The API trusts forwarded headers only from Caddy's fixed address.

Production cookies use browser-enforced prefixes:
- `__Secure-finguard_session`: Secure, HttpOnly, SameSite=Strict, Path=/api.
- `__Host-finguard_csrf`: Secure, Path=/, host-only.

Development and tests keep the unprefixed names over plain HTTP.

## D5. Test isolation (M1)
- Browser tests use `finguard_e2e_test`, and the backend suite uses `finguard_test`, so the two suites run back to back without restarts.
- Every destructive tool still refuses a database whose name does not end in `_test`.
- Base images are pinned by digest.
- `scripts/verify_clean_clone.py` records what a fresh clone without the dataset, model or `.env` does.

## D6. CI with a fixed expected-skip list (M8)
Approved option A. `.github/workflows/ci.yml` runs every check that works on a clean checkout, with PostgreSQL started from the same pinned image and role setup.

- **Expected skips:** the model binary and dataset are not in Git, so 298 tests skip, including every API test.
- **How the list is enforced:** `scripts/check_test_run.py` compares each run with `.github/expected-tests.json`. Any other skip, a missing listed skip, a changed reason, fewer passes than recorded, or no report fails the run.
- **What CI cannot show:** real-model inference, API, browser and HTTPS tests do not run in CI. They run locally before each commit.
- **Not yet run on GitHub:** nothing has been pushed, and no GitHub result is claimed.

## Further decisions

### Retention is a command (M5, approval decision 7)
`python -m app.commands.retention` removes data past its retention period:

| Data | Removed after |
|---|---|
| Ended sessions | 7 days |
| Audit records | 365 days |
| Rate-limit rows | 1 day |

It is a dry run unless given `--apply`. It reports counts and cutoff dates, and writes an audit entry. Nothing runs it on a schedule.

### Database outages answer 503 (M7)
An outage is a SQLAlchemy `DBAPIError` that either invalidated its connection or never reached a statement, as measured for refused, closed and killed connections. It answers 503 with `Retry-After: 5` and a message to retry. A statement timeout is not an outage and stays a 500.

Only the driver error's type is logged, because its message can name the host and role. The pool's pre-ping reconnects on the next request, with no restart.

### Optimistic concurrency for investigation status (M7)
`PATCH /investigations/{id}` accepts `expected_status`, which the Investigation Centre always sends. It is compared under the row lock, and a stale value answers 409 naming the current status. Assignment changes carry no expected value: the last change wins, and each is audited.

### The interface during failures (M7)
- **Start-up session check:** only a 401 means "signed out". Any other failure shows "FinGuard AI is unavailable" with Try again, keeping the session.
- **Page failures:** an error boundary around each page and around the app shows a reload prompt when a page fails to download or render.
- **Failed downloads:** error bodies are read before mapping, so the API's message and reference are shown.

### Screen readers (approval decision 8)
A manual Narrator/NVDA protocol is in [docs/accessibility/screen-reader-checklist.md](../accessibility/screen-reader-checklist.md). It stays marked UNTESTED until the owner runs it and records the results. No screen-reader compatibility is claimed.

### Not done in Phase 5
- Deployment.
- A public certificate.
- Shrinking the 1.92 GB API image (finding F12).
- Publishing the model binary for CI (D6 option B).
- Keyset pagination for deep explorer pages.

These are left for Phase 6 or recorded as limitations.
