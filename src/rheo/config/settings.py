"""Application settings with Pydantic for validation and env var support."""

import enum
import typing as t
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(enum.StrEnum):
    """Runtime environment for the application."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(enum.StrEnum):
    """Logging levels matching Loguru's standard levels."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application settings with sensible defaults.

    Can be populated from:
    - Defaults (defined here)
    - Environment variables (RHEO_* prefix)
    - CLI flags (highest priority, applied via build_settings)
    """

    # Core settings
    environment: Environment = Field(
        default=Environment.PRODUCTION,
        description="Runtime environment",
    )
    log_level: LogLevel = Field(
        default=LogLevel.WARNING,
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    download_dir: Path = Field(
        default_factory=lambda: Path.home() / "Downloads",
        description="Directory to save downloads",
    )

    # Download behavior
    max_concurrent: int = Field(
        default=3,
        ge=1,
        description="Maximum number of concurrent downloads",
    )
    chunk_size: int = Field(
        default=8192,
        ge=1024,
        description="Download chunk size in bytes",
    )
    timeout: float = Field(
        default=300.0,
        gt=0.0,
        description="Download timeout in seconds",
    )

    model_config = SettingsConfigDict(
        env_prefix="RHEO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def build_settings(**overrides: t.Any) -> Settings:
    """Build Settings with overrides applied.

    Loads from environment variables and applies overrides.
    Filters out None values from overrides.

    Args:
        **overrides: Keyword arguments to override default/env settings

    Returns:
        Settings instance

    Example:
        settings = build_settings(max_concurrent=5, log_level=LogLevel.DEBUG)
    """
    base_settings = Settings()

    # Filter out None values from overrides
    filtered_overrides = {k: v for k, v in overrides.items() if v is not None}

    # Create new settings with overrides
    if filtered_overrides:
        return base_settings.model_copy(update=filtered_overrides)

    return base_settings
