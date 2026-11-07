"""Temporal drift calculations, checked against hand calculations."""

import numpy as np
import pytest

from app.ml.drift import (
    build_prevalence_report,
    categorical_stability_index,
    decompose_prevalence_change,
    feature_drift,
    partition_prevalence,
    population_stability_index,
    prevalence_at_reference_volume,
    regime_by_hour,
    step_table_from_eda,
)
from app.ml.splitting import SplitBoundaries

BOUNDARIES = SplitBoundaries(first_step=1, train_end_step=2, validation_end_step=3, last_step=4)


def eda_summary():
    return {
        "whole_dataset": {
            "steps": [1, 2, 3, 4],
            "rows_per_step": [1000, 100, 1000, 100],
            "fraud_per_step": [10, 10, 5, 20],
        }
    }


def table():
    return step_table_from_eda(eda_summary(), BOUNDARIES)


def test_step_table_assigns_partitions_from_boundaries():
    assert table()["partition"].tolist() == ["train", "train", "validation", "test"]


def test_partition_summary_by_hand():
    summary = partition_prevalence(table(), cutoff=500)
    train = summary["train"]
    assert train["rows"] == 1100 and train["fraud_rows"] == 20
    assert train["prevalence"] == pytest.approx(20 / 1100)
    assert train["fraud_per_step"] == 10.0
    assert train["legitimate_per_step"] == 540.0
    assert train["regimes"]["sparse"]["steps"] == 1
    assert train["regimes"]["sparse"]["prevalence"] == pytest.approx(0.1)
    assert train["regimes"]["sparse"]["share_of_partition_fraud"] == pytest.approx(0.5)
    assert train["regimes"]["normal"]["share_of_partition_rows"] == pytest.approx(1000 / 1100)


def test_decomposition_effects_add_up_exactly():
    summary = partition_prevalence(table(), cutoff=500)
    result = decompose_prevalence_change(summary["train"], summary["test"])
    assert result["regime_mix_effect"] + result["within_regime_rate_effect"] == pytest.approx(
        result["total_change"]
    )


def test_decomposition_attributes_a_pure_mix_change_to_mix():
    # Rates are the same in both windows; only the share of sparse rows differs.
    regimes = {
        "sparse": {"prevalence": 0.1},
        "normal": {"prevalence": 0.01},
    }

    def window(sparse_share):
        return {
            "prevalence": sparse_share * 0.1 + (1 - sparse_share) * 0.01,
            "regimes": {
                "sparse": {**regimes["sparse"], "share_of_partition_rows": sparse_share},
                "normal": {**regimes["normal"], "share_of_partition_rows": 1 - sparse_share},
            },
        }

    result = decompose_prevalence_change(window(0.1), window(0.5))
    assert result["within_regime_rate_effect"] == pytest.approx(0.0)
    assert result["regime_mix_effect"] == pytest.approx(result["total_change"])


def test_prevalence_at_reference_volume_by_hand():
    value = prevalence_at_reference_volume({"legitimate_per_step": 990}, {"fraud_per_step": 10})
    assert value == pytest.approx(0.01)


def test_psi_of_identical_data_is_zero():
    values = np.random.default_rng(0).normal(size=5000)
    assert population_stability_index(values, values) == pytest.approx(0.0)


def test_psi_detects_a_shift():
    generator = np.random.default_rng(0)
    same = population_stability_index(generator.normal(size=5000), generator.normal(size=5000))
    moved = population_stability_index(generator.normal(size=5000), generator.normal(2, 1, 5000))
    assert same < 0.1 < 0.25 < moved


def test_categorical_psi_by_hand():
    reference = np.array(["a"] * 50 + ["b"] * 50)
    target = np.array(["a"] * 25 + ["b"] * 75)
    expected = (0.25 - 0.5) * np.log(0.25 / 0.5) + (0.75 - 0.5) * np.log(0.75 / 0.5)
    assert categorical_stability_index(reference, target, ["a", "b"]) == pytest.approx(expected)


def test_absent_category_does_not_give_infinity():
    value = categorical_stability_index(np.array(["a"] * 10), np.array(["b"] * 10), ["a", "b"])
    assert np.isfinite(value)


def test_regime_by_hour_reports_sparse_share():
    shares = regime_by_hour(table(), cutoff=500)
    assert shares["train"][2] == 1.0  # Step 2 has 100 rows and hour 2.
    assert shares["train"][1] == 0.0
    assert shares["train"][5] is None


def test_feature_drift_reports_all_rows_and_each_class(model_partition, later_partition):
    result = feature_drift(
        model_partition.features,
        model_partition.labels.to_numpy(),
        later_partition.features,
        later_partition.labels.to_numpy(),
    )
    assert set(result) == {"all_rows", "legitimate", "fraud"}
    assert set(result["all_rows"]) == {"amount_log1p", "transaction_type", "hour_of_day"}


def test_report_states_the_definition_uses_no_labels():
    report = build_prevalence_report(eda_summary(), BOUNDARIES, 500, [200])
    definition = report["regime_definition"]
    assert definition["uses_labels"] is False
    assert definition["available_at_serving"] is False
    assert "200" in report["cutoff_sensitivity"]
    assert len(report["daily_profile"]) == 1
