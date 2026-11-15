"""Application settings, read from the environment and validated once at start-up.

No credential has a default, so a missing value stops the application instead of letting it run
with something guessable.
"""

import ipaddress
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
    # Batch queue (Phase 5 M4). Each API process runs one worker that polls for jobs, holds a
    # lease it renews after every chunk, and gives up a job after this many interrupted attempts.
    batch_worker_enabled: bool = True
    batch_poll_seconds: float = Field(default=2.0, gt=0)
    batch_lease_seconds: int = Field(default=60, gt=0)
    batch_max_attempts: int = Field(default=3, gt=0)

    access_token_minutes: int = Field(default=30, gt=0)
    login_rate_limit_attempts: int = Field(default=5, gt=0)
    login_rate_limit_window_seconds: int = Field(default=60, gt=0)
    predict_rate_limit_per_minute: int = Field(default=120, gt=0)
    upload_rate_limit_per_minute: int = Field(default=10, gt=0)

    default_high_risk_boundary: float = Field(default=0.30, gt=0, le=1)
    model_report_path: Path = REPO_ROOT / "artifacts" / "metadata" / "model_v1_report.json"

    # Unset means Secure in production only, because browsers drop Secure cookies over plain HTTP.
    session_cookie_secure: bool | None = None
    # Comma-separated proxy addresses whose X-Forwarded-For is believed. Empty trusts nobody.
    trusted_proxy_ips: str = ""
    # Where rate-limit counts live. "database" is shared by every process and survives restarts;
    # "memory" is per process, kept for comparison measurements. Production requires "database".
    rate_limit_store: Literal["database", "memory"] = "database"
    # Interactive API documentation (/docs, /redoc, /openapi.json). Unset means on, except in
    # production, where it is off and may not be turned on (security finding S13, Phase 6). The
    # contract is published instead as API_DOCUMENTATION.md and frontend/openapi.json.
    api_docs_enabled: bool | None = None

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
        if self.app_env == "production" and self.session_cookie_secure is False:
            raise ValueError("Production session cookies must be Secure")
        if "*" in self.trusted_proxies:
            raise ValueError("TRUSTED_PROXY_IPS must list proxies, not a wildcard")
        for entry in self.trusted_proxies:
            check_proxy_entry(entry)
        if self.app_env == "production" and self.rate_limit_store != "database":
            raise ValueError("Production rate limits must be stored in the database")
        if self.app_env == "production" and self.api_docs_enabled:
            raise ValueError("Production must not serve the interactive API documentation")
        if self.app_env == "production" and not self.trusted_proxies:
            # Production cookies need HTTPS, which the API never terminates itself, so it always
            # runs behind a proxy. Without its address every user would share one sign-in limit.
            raise ValueError("Production must list its reverse proxy in TRUSTED_PROXY_IPS")
        return self

    @property
    def cors_origins(self) -> list[str]:
        """Return the allowed browser origins as a list."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def cookie_secure(self) -> bool:
        """Whether session cookies carry the Secure flag."""
        if self.session_cookie_secure is None:
            return self.app_env == "production"
        return self.session_cookie_secure

    @property
    def docs_enabled(self) -> bool:
        """Whether /docs, /redoc and /openapi.json are served."""
        if self.api_docs_enabled is None:
            return self.app_env != "production"
        return self.api_docs_enabled

    @property
    def trusted_proxies(self) -> list[str]:
        """Return the proxies allowed to report the client's address."""
        return [item.strip() for item in self.trusted_proxy_ips.split(",") if item.strip()]


def check_proxy_entry(entry: str) -> None:
    """Accept one address or network (host bits clear, as uvicorn requires); refuse all-covering."""
    try:
        network = ipaddress.ip_network(entry)
    except ValueError as error:
        raise ValueError(
            f"TRUSTED_PROXY_IPS entry {entry!r} is not an IP address or network"
        ) from error
    if network.prefixlen == 0:
        raise ValueError("TRUSTED_PROXY_IPS must not trust every address")


@lru_cache
def get_settings() -> Settings:
    """Return the validated settings, reading the environment only once."""
    return Settings()
