"""The performance harness's arithmetic: percentiles and the M3 latency budget rule."""

import pytest


def run(seq_p50, seq_p95, con_p50, con_p95):
    """A latency result with two identical rounds per mode."""
    rounds = {}
    for number in (1, 2):
        rounds[f"sequential_round_{number}"] = {"p50_ms": seq_p50, "p95_ms": seq_p95}
        rounds[f"concurrent_8_round_{number}"] = {"p50_ms": con_p50, "p95_ms": con_p95}
    return {"prediction_latency": rounds}


@pytest.fixture
def harness(load_script):
    return load_script("measure_performance")


def test_nearest_rank_percentiles(harness):
    stats = harness.summarise([float(n) for n in range(1, 101)])
    assert (stats["n"], stats["p50_ms"], stats["p95_ms"], stats["p99_ms"], stats["max_ms"]) == (
        100,
        50.0,
        95.0,
        99.0,
        100.0,
    )


def test_overhead_within_budget_is_accepted(harness):
    baseline = [run(30, 40, 300, 400), run(30, 40, 300, 400)]
    candidate = [run(32, 45, 320, 450), run(32, 45, 320, 450)]
    result = harness.compare_runs(baseline, candidate)
    assert result["accepted"] is True
    assert result["checks"]["sequential_p50_ms"]["allowed_ms"] == 3.0


@pytest.mark.parametrize(
    "candidate,failing",
    [
        (run(33.5, 40, 300, 400), "sequential_p50_ms"),  # +3.5 ms > 10% of 30
        (run(30, 46.5, 300, 400), "sequential_p95_ms"),  # +6.5 ms > 15% of 40
        (run(30, 40, 331, 400), "concurrent_p50_ms"),
        (run(30, 40, 300, 461), "concurrent_p95_ms"),
    ],
)
def test_any_statistic_over_budget_rejects(harness, candidate, failing):
    result = harness.compare_runs([run(30, 40, 300, 400)], [candidate])
    assert result["accepted"] is False
    assert not result["checks"][failing]["within_budget"]


def test_small_baselines_get_the_two_millisecond_floor(harness):
    result = harness.compare_runs([run(10, 12, 100, 120)], [run(11.9, 13.9, 100, 120)])
    assert result["checks"]["sequential_p50_ms"]["allowed_ms"] == 2.0
    assert result["accepted"] is True
