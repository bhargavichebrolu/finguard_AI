"""Tests that a bad configuration stops the application instead of running with it."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.frozen_model import FROZEN_MODEL_SHA256, FROZEN_THRESHOLD, SCORE_IS_CALIBRATED

GOOD = {
    "database_url": "postgresql+psycopg://user:realpassword@127.0.0.1:5432/finguard",
    "secret_key": "k" * 40,
    "_env_file": None,
}


def build(**overrides) -> Settings:
    return Settings(**{**GOOD, **overrides})


def test_valid_settings_are_accepted():
    assert build().cors_origins == ["http://localhost:5173"]


def test_secret_key_cannot_be_short():
    with pytest.raises(ValidationError, match="at least 32"):
        build(secret_key="short")


@pytest.mark.parametrize("secret", ["replace-with-a-long-random-value-" + "x" * 10])
def test_secret_key_cannot_be_the_template_value(secret):
    with pytest.raises(ValidationError, match="placeholder"):
        build(secret_key=secret)


def test_database_url_cannot_be_the_template_value():
    with pytest.raises(ValidationError, match="placeholder"):
        build(database_url="postgresql+psycopg://finguard_app:change-me@127.0.0.1:5432/finguard")


def test_wildcard_cors_is_refused_everywhere():
    with pytest.raises(ValidationError, match="wildcard"):
        build(cors_allowed_origins="*")


def test_production_refuses_localhost_origins():
    with pytest.raises(ValidationError, match="localhost"):
        build(app_env="production", cors_allowed_origins="http://localhost:5173")


def test_production_refuses_per_process_rate_limits():
    # Phase 5 M3: per-process counts multiply the limits and reset on every restart.
    with pytest.raises(ValidationError, match="rate limits must be stored in the database"):
        build(
            app_env="production",
            cors_allowed_origins="https://a.example",
            rate_limit_store="memory",
        )
    assert build(rate_limit_store="memory").rate_limit_store == "memory"  # allowed outside it
    assert build().rate_limit_store == "database"


def test_production_accepts_a_real_origin():
    settings = build(
        app_env="production", cors_allowed_origins="https://a.example, https://b.example"
    )
    assert settings.cors_origins == ["https://a.example", "https://b.example"]


def test_secrets_do_not_appear_when_settings_are_printed():
    text = repr(build())
    assert "realpassword" not in text
    assert "k" * 40 not in text


def test_validation_error_does_not_contain_the_secret():
    with pytest.raises(ValidationError) as caught:
        build(secret_key="tooshortsecret")
    assert "tooshortsecret" not in caught.value.errors(include_input=False).__repr__()


def test_frozen_values_match_phase_2():
    assert FROZEN_THRESHOLD == 0.02841914258897305
    assert FROZEN_MODEL_SHA256.startswith("69813c17")
    assert SCORE_IS_CALIBRATED is False
