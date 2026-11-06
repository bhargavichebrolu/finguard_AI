"""Feature schema tests: the leakage rules from PRD 4.3 hold in the declared schema."""

import json

from app.ml.schema import (
    ACCOUNT_IDENTIFIER_COLUMNS,
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    FEATURE_DICTIONARY,
    FORBIDDEN_FEATURE_COLUMNS,
    LEAKY_BALANCE_COLUMNS,
    NUMERIC_FEATURES,
    PIPELINE_RAW_COLUMNS,
    RAW_COLUMNS,
    RULE_FLAG_COLUMN,
    TARGET_COLUMN,
    feature_dictionary_records,
)


def test_features_exclude_every_forbidden_column():
    assert not set(FEATURE_COLUMNS) & FORBIDDEN_FEATURE_COLUMNS


def test_target_and_rule_flag_are_forbidden():
    assert {TARGET_COLUMN, RULE_FLAG_COLUMN} <= FORBIDDEN_FEATURE_COLUMNS


def test_pipeline_never_reads_balances_or_origin_account():
    assert not set(PIPELINE_RAW_COLUMNS) & set(LEAKY_BALANCE_COLUMNS)
    assert "nameOrig" not in PIPELINE_RAW_COLUMNS
    assert set(PIPELINE_RAW_COLUMNS) <= set(RAW_COLUMNS)


def test_identifiers_are_not_features():
    assert not set(FEATURE_COLUMNS) & set(ACCOUNT_IDENTIFIER_COLUMNS)


def test_every_feature_is_available_before_completion():
    assert all(spec.available_before_completion for spec in FEATURE_DICTIONARY)


def test_every_feature_has_complete_documentation():
    for spec in FEATURE_DICTIONARY:
        assert spec.source_columns and spec.transformation and spec.data_type
        assert spec.business_meaning and spec.rationale
        assert spec.kind in {"numeric", "categorical"}
        assert set(spec.source_columns) <= set(RAW_COLUMNS)


def test_numeric_and_categorical_lists_cover_all_features_once():
    assert sorted(NUMERIC_FEATURES + CATEGORICAL_FEATURES) == sorted(FEATURE_COLUMNS)


def test_feature_dictionary_records_are_json_serialisable():
    records = feature_dictionary_records()
    assert json.loads(json.dumps(records))["feature_schema_version"]
    assert [item["name"] for item in records["features"]] == list(FEATURE_COLUMNS)
    assert records["rejected_features"]
