# test_measure_performance.py

Source: [backend/tests/unit/test_measure_performance.py](test_measure_performance.py)

## A. File Purpose
Tests the performance harness's percentile arithmetic and the M3 latency budget rule.

## B. Why This File Exists
The decision to accept or reject the database rate limiter rests on this rule, so it is tested, not trusted.

## C. Dependencies
- **Libraries:** pytest.
- **Internal modules:** `scripts/measure_performance.py` through `load_script`.
- **External services / database:** none.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `run`
Builds a latency result with two identical rounds per mode.

### `harness`
Fixture: the loaded script.

## E. Classes Explained
None.

## F. Execution Flow
Feed constructed results to `summarise` and `compare_runs`.

## G. Input and Output
| Test | Proves |
|---|---|
| `test_nearest_rank_percentiles` | p50, p95, p99 and max on 1 to 100. |
| `test_overhead_within_budget_is_accepted` | Acceptance. |
| `test_any_statistic_over_budget_rejects` | Each of the four checks can reject alone. |
| `test_small_baselines_get_the_two_millisecond_floor` | The floor. |

## H. Important Technical Concepts
- **Hand-chosen numbers** sit just over or under each limit.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_measure_performance.py --rootdir backend -c backend/pyproject.toml
```

## J. Maintenance Notes
If the budget changes, change it in the baseline document first.

## K. Related Files
- [measure_performance.py](../../../scripts/measure_performance.py.explanation.md): the harness.
