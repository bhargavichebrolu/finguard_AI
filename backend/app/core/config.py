"""Application settings, read from the environment and validated once at start-up.

No credential has a default, so a missing value stops the application instead of letting it run
with something guessable.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_VERSION = "0.3.0"
MINIMUM_SECRET_KEY_LENGTH = 32
_PLACEHOLDER_MARKERS = ("change-me", "replace-with")


class Settings(BaseSettings):
    """Every setting the API reads. Field names match environment variables, ignoring case."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr
    secret_key: SecretStr
    cors_allowed_origins: str = "http://localhost:5173"

    model_metadata_path: Path = REPO_ROOT / "artifacts" / "metadata" / "model_v1.json"
    model_metrics_path: Path = REPO_ROOT / "artifacts" / "metadata" / "model_v1_metrics.json"
    preprocessing_metadata_path: Path = (
        REPO_ROOT / "artifacts" / "metadata" / "preprocessing_v1.json"
    )
    model_artifact_dir: Path = REPO_ROOT / "artifacts" / "models"

    upload_tmp_dir: Path = REPO_ROOT / "backend" / "tmp"
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    max_batch_rows: int = Field(default=50_000, gt=0)
    batch_chunk_rows: int = Field(default=1_000, gt=0)
    max_stored_row_errors: int = Field(default=1_000, gt=0)

    access_token_minutes: int = Field(default=30, gt=0)
    login_rate_limit_attempts: int = Field(default=5, gt=0)
    login_rate_limit_window_seconds: int = Field(default=60, gt=0)
    predict_rate_limit_per_minute: int = Field(default=120, gt=0)
    upload_rate_limit_per_minute: int = Field(default=10, gt=0)

    default_high_risk_boundary: float = Field(default=0.30, gt=0, le=1)

    @field_validator("secret_key")
    @classmethod
    def _secret_key_must_be_real(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret) < MINIMUM_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY must have at least {MINIMUM_SECRET_KEY_LENGTH} characters"
            )
        if any(marker in secret for marker in _PLACEHOLDER_MARKERS):
            raise ValueError("SECRET_KEY still holds the template placeholder")
        return value

    @field_validator("database_url")
    @classmethod
    def _database_url_must_be_real(cls, value: SecretStr) -> SecretStr:
        if any(marker in value.get_secret_value() for marker in _PLACEHOLDER_MARKERS):
            raise ValueError("DATABASE_URL still holds the template placeholder")
        return value

    @model_validator(mode="after")
    def _origins_must_be_explicit(self) -> "Settings":
        origins = self.cors_origins
        if "*" in origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must list origins, not a wildcard")
        if self.app_env == "production" and any("localhost" in origin for origin in origins):
            raise ValueError("Production must not allow localhost as a CORS origin")
        return self

    @property
    def cors_origins(self) -> list[str]:
        """Return the allowed browser origins as a list."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the validated settings, reading the environment only once."""
    return Settings()
