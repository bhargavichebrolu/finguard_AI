# 20261109_0003_rate_limit_events.py

Source: [backend/migrations/versions/20261109_0003_rate_limit_events.py](20261109_0003_rate_limit_events.py)

## A. File Purpose
Creates the two rate-limit tables: `rate_limit_events` (sliding-window events) and `rate_limit_windows` (fixed-window counters).

## B. Why This File Exists
Phase 5 M3 moved rate-limit counts from process memory to PostgreSQL, so they are shared by every process and survive restarts.

## C. Dependencies
- **Libraries:** Alembic, SQLAlchemy.
- **Internal modules:** none.
- **External services / database:** PostgreSQL.
- **Depended on by:** `alembic upgrade head`, the `migrate` and `migrate-e2e` services, `test_migrations.py`.

## D. Every Function Explained

### `upgrade`
Creates `rate_limit_events` (identity id, key, `occurred_at` defaulting to `clock_timestamp()`, index on key and time) and `rate_limit_windows` (key and window start as the primary key, and a count).

### `downgrade`
Drops both tables and the index.

## E. Classes Explained
None.

## F. Execution Flow
Runs after revision 0002.

## G. Input and Output
Output: two tables.

## H. Important Technical Concepts
- **`clock_timestamp()`** gives the time of the insert itself, not of the transaction's start, so events are timed when they happen.

## I. Example
```powershell
uv run alembic upgrade head
```

## J. Maintenance Notes
Keep in step with `RateLimitEvent` and `RateLimitWindow` in `records.py`; `test_models_and_migrations_agree` checks it.

## K. Related Files
- [rate_limit.py](../../app/core/rate_limit.py.explanation.md): the users of these tables.
