"""Typed application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogFormat = Literal["console", "json"]
Locale = Literal["uz", "ru"]


def _default_locales() -> list[Locale]:
    """Return the ordered locale defaults."""
    return ["uz", "ru"]


def _split_csv(value: object) -> object:
    """Convert comma-separated environment values to a clean list."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


CsvList = Annotated[list[str], NoDecode, BeforeValidator(_split_csv)]
LocaleList = Annotated[list[Locale], NoDecode, BeforeValidator(_split_csv)]


class Settings(BaseSettings):
    """Validated runtime settings. Secret-bearing fields (Telegram token) are never logged."""

    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="Kalibr Publisher", validation_alias="APP_NAME")
    app_env: Environment = Field(default="development", validation_alias="APP_ENV")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    app_domain: str = Field(default="localhost", validation_alias="APP_DOMAIN")
    timezone: str = Field(default="Asia/Tashkent", validation_alias="APP_TIMEZONE")
    default_locale: Locale = Field(default="uz", validation_alias="APP_DEFAULT_LOCALE")
    supported_locales: LocaleList = Field(
        default_factory=_default_locales,
        validation_alias="APP_SUPPORTED_LOCALES",
    )

    telegram_bot_token: str | None = Field(
        default=None,
        validation_alias="TELEGRAM_BOT_TOKEN",
        description="Telegram Bot API token. Never logged or exposed via the API.",
    )
    telegram_default_channel: str | None = Field(
        default=None,
        validation_alias="TELEGRAM_DEFAULT_CHANNEL",
        description="Default Telegram channel/username posts are sent to, e.g. @inglizguru.",
    )
    # --- AI (Gemini) ---
    gemini_api_key: str = Field(default="", description="Google Gemini API key for caption AI.")
    gemini_model: str = Field(default="gemini-flash-latest", description="Gemini model for caption tasks.")
    ai_caption_language: str = Field(default="uz", description="Target language for AI-rewritten captions (uz/ru/en).")
    ai_enabled: bool = Field(default=True, description="Enable AI caption rewrite/translate before sending.")

    # --- Media & storage ---
    media_root: str = Field(default="storage/media", description="Directory for uploaded media files.")
    max_upload_mb: int = Field(default=20, description="Max upload size per file in MB.")

    # --- Scheduler ---

    scheduler_poll_seconds: int = Field(default=30, description="How often the scheduler checks for due posts.")
    default_recurring_hours: int = Field(default=24, description="Default spacing for recurring batches.")

    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=8000, ge=1, le=65535, validation_alias="API_PORT")
    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")
    allowed_hosts: CsvList = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "api"],
        validation_alias="API_ALLOWED_HOSTS",
    )
    cors_origins: CsvList = Field(
        default_factory=lambda: ["http://localhost:3000"],
        validation_alias="API_CORS_ORIGINS",
    )
    docs_enabled: bool = Field(default=True, validation_alias="API_DOCS_ENABLED")
    log_level: str = Field(default="INFO", validation_alias="API_LOG_LEVEL")
    log_format: LogFormat = Field(default="console", validation_alias="API_LOG_FORMAT")
    request_id_header: str = Field(
        default="X-Request-ID",
        validation_alias="API_REQUEST_ID_HEADER",
    )

    storage_root: Path = Field(default=Path("/app/data/storage"), validation_alias="STORAGE_ROOT")
    backup_root: Path = Field(default=Path("/app/data/backups"), validation_alias="BACKUP_ROOT")
    temp_root: Path = Field(default=Path("/app/data/tmp"), validation_alias="TEMP_ROOT")
    log_root: Path = Field(default=Path("/app/data/logs"), validation_alias="LOG_ROOT")

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        """Require a normalized absolute API prefix."""
        normalized = value.rstrip("/")
        if not normalized.startswith("/") or normalized == "":
            msg = "API_V1_PREFIX must be an absolute non-root path"
            raise ValueError(msg)
        return normalized

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normalize and validate the configured Python log level."""
        normalized = value.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in allowed:
            msg = f"API_LOG_LEVEL must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return normalized

    @field_validator("supported_locales")
    @classmethod
    def ensure_locales_are_unique(cls, value: list[Locale]) -> list[Locale]:
        """Preserve locale order while rejecting duplicate configuration."""
        if len(value) != len(set(value)):
            msg = "APP_SUPPORTED_LOCALES cannot contain duplicates"
            raise ValueError(msg)
        if not value:
            msg = "APP_SUPPORTED_LOCALES must contain at least one locale"
            raise ValueError(msg)
        return value

    def model_post_init(self, __context: object) -> None:
        """Validate relationships between settings after field parsing."""
        if self.default_locale not in self.supported_locales:
            msg = "APP_DEFAULT_LOCALE must be included in APP_SUPPORTED_LOCALES"
            raise ValueError(msg)
        if self.app_env == "production" and "*" in self.allowed_hosts:
            msg = "Wildcard API_ALLOWED_HOSTS is forbidden in production"
            raise ValueError(msg)

    @property
    def is_production(self) -> bool:
        """Return whether production-safe behavior should be enabled."""
        return self.app_env == "production"

    @property
    def runtime_directories(self) -> tuple[Path, ...]:
        """Return directories that must exist and be writable."""
        return (self.storage_root, self.backup_root, self.temp_root, self.log_root)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide immutable settings instance."""
    return Settings()
