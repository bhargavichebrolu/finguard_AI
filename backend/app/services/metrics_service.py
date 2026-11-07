"""Describe the frozen Phase 2 results. Every figure comes from the saved metrics file.

Nothing is recalculated here, and the test partition is not read. The notes are built from saved
values, so they cannot drift from them.
"""

from typing import Any


def performance_notes(metrics: dict[str, Any]) -> list[str]:
    """Return plain statements of what the saved results show, including the shortfalls."""
    test = metrics["test"]["at_frozen_threshold"]
    normal = metrics["test"]["regimes"]["normal"]["at_frozen_threshold"]
    sparse = metrics["test"]["regimes"]["sparse"]["at_frozen_threshold"]
    validation = metrics["validation"]["at_threshold"]
    validation_rate = metrics["validation"]["ranking"]["prevalence"]
    test_rate = metrics["test"]["ranking"]["prevalence"]
    target = metrics["threshold"]["operational_fpr_cap"]
    multiple = test["false_positive_rate"] / target
    return [
        (
            f"The false positive rate on the test partition was {test['false_positive_rate']:.3%}, "
            f"which is {multiple:.1f} times the {target:.1%} target set on validation. "
            "The target was not met on test."
        ),
        (
            f"Overall recall on test was {test['recall']:.1%}, so "
            f"{test['false_negative_rate']:.1%} of labelled fraud was not flagged."
        ),
        (
            f"Recall was {normal['recall']:.1%} in normal steps and {sparse['recall']:.1%} in "
            "sparse steps on test."
        ),
        (f"Precision on test was {test['precision']:.1%}, so most flags were not labelled fraud."),
        (
            f"The fraud rate was {validation_rate:.3%} on validation and {test_rate:.3%} on test. "
            f"Validation precision was {validation['precision']:.1%}. Test's higher precision "
            "partly reflects its higher fraud rate, so it is not evidence of improvement."
        ),
        (
            "model_score is not calibrated. It ranks transactions and must not be read as a "
            "probability of fraud."
        ),
        "All results come from the synthetic PaySim simulator and may not apply to real payments.",
    ]


def feature_importance(metrics: dict[str, Any]) -> dict[str, Any]:
    """Return saved global importance, with the limits of what it shows."""
    importance = metrics["global_feature_importance"]
    return {
        "model_version": metrics["model_version"],
        "output_scale": importance["output_scale"],
        "by_group": importance["by_group"],
        "by_feature": importance["by_feature"],
        "limitations": metrics["explanation_limitations"],
    }


def evaluation_rows(metrics: dict[str, Any]) -> list[tuple[str, str, str, Any]]:
    """Flatten the saved results into rows of partition, slice, metric and value."""
    sections = [
        ("validation", "all", metrics["validation"]["at_threshold"]),
        ("validation", "all", metrics["validation"]["ranking"]),
        ("test", "all", metrics["test"]["at_frozen_threshold"]),
        ("test", "all", metrics["test"]["ranking"]),
    ]
    for regime, values in metrics["test"]["regimes"].items():
        sections.append(("test", f"{regime}_steps", values["at_frozen_threshold"]))
        sections.append(("test", f"{regime}_steps", values["ranking"]))
    rows = [
        (partition, part, name, value)
        for partition, part, values in sections
        for name, value in values.items()
    ]
    rows.append(
        ("target", "all", "false_positive_rate_target", metrics["threshold"]["operational_fpr_cap"])
    )
    return rows
