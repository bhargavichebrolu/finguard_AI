# measure_performance.py

Source: [scripts/measure_performance.py](measure_performance.py)

## A. File Purpose
Measures the running system and writes every figure to a JSON file; renders Markdown tables only from such a file.

## B. Why This File Exists
Phase 5 requires measured performance and forbids invented metrics. M3's shared rate limits must also be accepted or rejected against a latency budget set from these measurements.

## C. Dependencies
- **Libraries:** httpx, Python standard library.
- **Internal modules:** `scripts/e2e_database.py` (reseed).
- **External services / database:** The browser-test API on 127.0.0.1:8011 and its database `finguard_e2e_test`; Docker (`docker stats`, `docker info`).
- **Depended on by:** Developers; results in `docs/performance/`.

## D. Every Function Explained

### `summarise`
Count, mean and nearest-rank p50, p95 and p99, and the maximum, of a list of milliseconds.

### `rank`
Nested in `summarise`: the nearest-rank percentile.

### `synthetic_rows`
Generates synthetic transactions from a seeded random generator: a random type, an amount from 1 to 5,000,000, a step from 1 to 743, and a merchant destination only for PAYMENT. No PaySim data is read.

### `as_csv`
Turns rows into an upload file with the API's column names.

### `session`
Signs in through `POST /auth/session` with the allowed origin and keeps the CSRF header, so requests take the interface's cookie path.

### `create_perf_users`
Creates 40 synthetic analyst accounts through the administrator API, so load is spread across accounts and the production rate limits stay unchanged.

### `prediction_latency`
- **Purpose:** measure `POST /transactions/predict`.
- **Parameters / types:** signed-in clients, a seeded generator, a run id. **Returns / type:** statistics per run.
- **Internal processing:** 40 warm-up requests, then two rounds of 400 sequential and 1,600 concurrent requests (8 threads). Two rounds show run-to-run variation.
- **Error handling:** any status other than 201 stops the run. **Calls:** `summarise`. **Used by:** `command_run`, `command_latency`.

### `one`
Nested: one timed prediction.

### `payloads`
Nested: a fresh set of synthetic inputs with unique identifiers.

### `worker`
Nested: one concurrent client's share of the requests.

### `run_batch`
Uploads rows as a CSV, polls until the job finishes, and returns rows per second from the server's own start and finish times.

### `stored_total`
The number of stored transactions, from the explorer's total.

### `populate`
Uploads 50,000-row batches through the real batch path until the database holds the target number of predictions.

### `time_request`
Two warm-up calls, then a repeated GET, summarised.

### `query_timings`
Times the explorer (newest, high risk, type and amount, identifier search, highest score, last page), the dashboard summary, the investigation queue and the full predictions CSV export at the current volume.

### `container_memory`
The API container's memory from `docker stats`.

### `environment`
Records the time, commit, host, Docker virtual machine and measurement path with the results.

### `bundle_sizes`
Raw and gzip sizes of the built frontend files.

### `reseed`
Runs `e2e_database.py seed`, emptying the browser-test database first.

### `admin_client`
Signs in as the seeded administrator.

### `command_run`
The full baseline: latency, batches, volumes of 100,000 and 500,000 with their queries, memory at each point, and bundle sizes.

### `step`
Runs one measurement, stores and prints it.

### `command_latency`
Repeats only the prediction latency measurement, with a label, for before-and-after comparisons.

### `command_render`
Prints the Markdown for a results file, with optional page timings.

### `row`
One Markdown table row.

### `render`
Builds the Markdown tables from a results file only, with a note that it is generated.

### `main`
Parses the `run`, `latency` and `render` commands.

### `command_queries`
Times the explorer, dashboard, queue and (unless `--no-export`) export queries at the volume already stored, without reseeding, and records memory. Used for before-and-after comparisons on the same data.

### `compare_runs`
Applies the M3 budget: for sequential and concurrent requests, the median p50 and p95 across all runs and rounds of each condition; the candidate may exceed the baseline by at most 10 % (p50) or 15 % (p95) of the baseline, with a 2 ms floor.

### `median_of`
Nested in `compare_runs`: the median of one statistic over runs.

### `command_compare`
Loads paired run files, applies `compare_runs`, writes the decision and exits 1 if rejected.

### `load`
Nested in `command_compare`: reads the run files.

### `command_batches`
Measures batch throughput only, at 1,000, 10,000 and 50,000 rows, after reseeding.

## E. Classes Explained
None.

## F. Execution Flow
Reseed, create accounts, measure, write JSON; later, render Markdown from the JSON.

## G. Input and Output
Output: a JSON results file. `render` prints Markdown.

## H. Important Technical Concepts
- **`BUDGET` and `BUDGET_FLOOR_MS`** hold the rule fixed in `docs/performance/phase-5-baseline.md` before M3 code existed.
- **Same limits as production:** load is spread over many accounts rather than raising the per-user rate limits.
- **Server-side batch timing:** rows per second use the job's own `created_at` and `completed_at`.
- **Direct path:** requests go straight to the API, not through the preview proxy, so these are API figures.

## I. Example
```powershell
python scripts/measure_performance.py run --out docs/performance/phase-5-baseline.json
python scripts/measure_performance.py render docs/performance/phase-5-baseline.json --pages docs/performance/phase-5-pages.json
```

## J. Maintenance Notes
Never edit a results file or rendered table by hand. Re-run instead.

## K. Related Files
- [pages.perf.ts](../frontend/tests/perf/pages.perf.ts.explanation.md): page timings.
