# Phase 5 M3: shared rate limits and worker count

Every figure is read from the saved JSON files named below, produced by `scripts/measure_performance.py` on the browser-test stack. The method and budget were fixed in [phase-5-baseline.md](phase-5-baseline.md) before any M3 code was written.

## Rate-limit latency budget: two candidates

Each candidate was compared in one session with the memory store, in the order memory, database, memory, database; each run is two rounds of 400 sequential and 1,600 concurrent (8 clients) predictions.

### Candidate 1: sliding window, advisory lock (rejected)

Runs: phase-5-ratelimit-sliding-1-memory.json, phase-5-ratelimit-sliding-3-memory.json (memory); phase-5-ratelimit-sliding-2-database.json, phase-5-ratelimit-sliding-4-database.json (database). Decision file: `phase-5-ratelimit-sliding-decision.json`.

| Check | Memory ms | Database ms | Overhead ms | Allowed ms | Within budget |
|---|---|---|---|---|---|
| sequential_p50_ms | 23.57 | 26.66 | 3.08 | 2.36 | no |
| sequential_p95_ms | 27.66 | 33.09 | 5.43 | 4.15 | no |
| concurrent_p50_ms | 177.06 | 208.02 | 30.96 | 17.71 | no |
| concurrent_p95_ms | 229.26 | 263.65 | 34.38 | 34.39 | yes |

**rejected for the prediction path: three of four checks over budget**

### Candidate 2: fixed one-minute window, one autocommit upsert (accepted)

Runs: phase-5-ratelimit-window-1-memory.json, phase-5-ratelimit-window-3-memory.json (memory); phase-5-ratelimit-window-2-database.json, phase-5-ratelimit-window-4-database.json (database). Decision file: `phase-5-ratelimit-window-decision.json`.

| Check | Memory ms | Database ms | Overhead ms | Allowed ms | Within budget |
|---|---|---|---|---|---|
| sequential_p50_ms | 25.19 | 23.63 | -1.55 | 2.52 | yes |
| sequential_p95_ms | 29.13 | 26.63 | -2.5 | 4.37 | yes |
| concurrent_p50_ms | 190.06 | 182.9 | -7.16 | 19.01 | yes |
| concurrent_p95_ms | 250.46 | 229.74 | -20.73 | 37.57 | yes |

**accepted for predictions and uploads: all four checks within budget; the differences are within run-to-run noise (the database runs were slightly faster)**

Negative overheads mean the database runs happened to be faster: the difference is within run-to-run noise. Failed sign-ins keep the sliding window (not on the prediction path), because a fixed window could admit up to twice the limit across a minute boundary, which matters for guessing; for prediction and upload limits that trade-off is accepted.

## Worker count (database rate limits)

| Workers | Sequential p50 ms (rounds) | 8-concurrent p50 ms (rounds) | 8-concurrent p95 ms (round 2) | Requests/s, concurrent (rounds) | Memory idle | Memory after | File |
|---|---|---|---|---|---|---|---|
| 1 | 24.2, 23.08 | 187.12, 195.56 | 254.43 | 42.1, 40.4 | 166.5MiB | 181.6MiB | `phase-5-workers-1.json` |
| 2 | 24.89, 24.27 | 94.56, 98.23 | 192.69 | 75.1, 74.1 | 345.4MiB | 381.4MiB | `phase-5-workers-2.json` |
| 4 | 23.69, 24.34 | 177.77, 173.4 | 222.24 | 46.0, 48.5 | 654.5MiB | 704.8MiB | `phase-5-workers-4.json` |

Idle memory was read with `docker stats` just after each start (recorded in the run log, not in the JSON).

**Decision:** the default stays at one worker (`WEB_CONCURRENCY=1`), which leaves headroom in a 512 MB container for batches and exports. Two workers nearly doubled concurrent throughput here and are recommended where at least 1 GB is available. Four workers were slower than two, most likely because each worker's model scoring competes for the same CPU cores; per-worker thread limits are a possible tuning for Phase 6, not made here.

**Batches:** until M4, more than one worker is not safe for CSV batches, because start-up recovery in one process can fail another process's running job (finding F1). M4 replaces that logic.
