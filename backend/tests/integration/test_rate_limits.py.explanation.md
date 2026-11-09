# test_rate_limits.py

Source: [backend/tests/integration/test_rate_limits.py](test_rate_limits.py)

## A. File Purpose
Tests the rate-limit stores: exact limits, waits, expiry, the sign-in pattern, simultaneous requests and restarts.

## B. Why This File Exists
Rate limits are a security control; moving them to PostgreSQL (Phase 5 M3) must keep them exact under concurrency.

## C. Dependencies
- **Libraries:** pytest, SQLAlchemy.
- **Internal modules:** `app.core.rate_limit`.
- **External services / database:** PostgreSQL (`finguard_test`).
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `database_limiter`
Fixture: a database limiter on empty tables.

### `any_limiter`
Fixture parametrised over the memory and database stores, so both obey the same rules.

### `attempt`
Nested helper: one attempt that reports whether it was allowed.

## E. Classes Explained
None.

## F. Execution Flow
Each `hit` takes its own connection and transaction, as in separate processes.

## G. Input and Output
| Test | Proves |
|---|---|
| `test_allows_exactly_the_limit_then_refuses_with_a_wait` | Exact limit, a wait between 1 and 61 seconds, other keys unaffected. |
| `test_refused_attempts_are_not_counted` | Refusals do not extend the block. |
| `test_events_expire_after_the_window` | Sliding expiry. |
| `test_sign_in_pattern_check_record_and_clear` | The sign-in sequence. |
| `test_simultaneous_requests_never_exceed_the_limit` | 20 at once admit exactly 5 (sliding). |
| `test_expired_events_are_deleted_as_the_key_is_used` | The table stays small. |
| `test_counts_use_database_time_and_survive_a_new_limiter` | A new limiter (a restarted process) sees old counts. |
| `test_fixed_window_allows_exactly_the_limit` | Fixed window: exact limit and a wait. |
| `test_fixed_window_admits_exactly_the_limit_under_simultaneous_requests` | 20 at once admit exactly 5 (fixed). |
| `test_fixed_window_starts_again_in_the_next_window` | Window rollover. |

## H. Important Technical Concepts
- **Short windows** of one or two seconds keep expiry tests fast.

## I. Example
```powershell
uv run --project backend pytest backend/tests/integration/test_rate_limits.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
Keep both stores in `any_limiter` while both exist.

## K. Related Files
- [rate_limit.py](../../app/core/rate_limit.py.explanation.md): the code under test.
