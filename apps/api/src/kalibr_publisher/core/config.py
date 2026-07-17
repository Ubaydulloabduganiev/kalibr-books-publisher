"""Typed application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogFormat = Literal["console", "json"]
Locale = Literal["uz", "ru"]


def _split_csv(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


CsvList = Annotated[list[str], NoDecode, BeforeValidator(_split_csv)]
LocaleList = Annotated[list[Locale], NoDecode, BeforeValidator(_split_csv)]


def _default_locales() -> list[Locale]:
    return ["uz", "ru"]


class Settings(BaseSettings):
    """Validated runtime settings. Secret fields are never exposed by public APIs."""

    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="Kalibr Publisher", validation_alias="APP_NAME")
    app_env: Environment = Field(default="development", validation_alias="APP_ENV")
    app_version: str = Field(default="0.1.1", validation_alias="APP_VERSION")
    app_domain: str = Field(default="localhost", validation_alias="APP_DOMAIN")
    timezone: str = Field(default="Asia/Tashkent", validation_alias="APP_TIMEZONE")
    default_locale: Locale = Field(default="uz", validation_alias="APP_DEFAULT_LOCALE")
    supported_locales: LocaleList = Field(
        default_factory=_default_locales, validation_alias="APP_SUPPORTED_LOCALES"
    )

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
    request_id_header: str = Field(default="X-Request-ID", validation_alias="API_REQUEST_ID_HEADER")
    internal_api_key: SecretStr | None = Field(default=None, validation_alias="INTERNAL_API_KEY")

    storage_root: Path = Field(default=Path("/app/data/storage"), validation_alias="STORAGE_ROOT")
    backup_root: Path = Field(default=Path("/app/data/backups"), validation_alias="BACKUP_ROOT")
    temp_root: Path = Field(default=Path("/app/data/tmp"), validation_alias="TEMP_ROOT")
    log_root: Path = Field(default=Path("/app/data/logs"), validation_alias="LOG_ROOT")
    max_upload_mb: int = Field(default=100, ge=1, le=2000, validation_alias="MAX_UPLOAD_MB")
    scheduler_poll_seconds: int = Field(
        default=15, ge=5, le=3600, validation_alias="SCHEDULER_POLL_SECONDS"
    )

    telegram_bot_token: SecretStr | None = Field(
        default=None, validation_alias="TELEGRAM_BOT_TOKEN"
    )
    telegram_default_channel: str | None = Field(
        default=None, validation_alias="TELEGRAM_DEFAULT_CHANNEL"
    )

    gemini_api_key: SecretStr | None = Field(
        default=None, validation_alias="GEMINI_API_KEY"
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash-image",
        validation_alias="GEMINI_MODEL",
    )
    gemini_text_model: str = Field(
        default="gemini-2.5-flash", validation_alias="GEMINI_TEXT_MODEL"
    )
    ai_caption_language: str = Field(default="uz", validation_alias="AI_CAPTION_LANGUAGE")
    ai_enabled: bool = Field(default=True, validation_alias="AI_ENABLED")

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith("/") or normalized == "":
            raise ValueError("API_V1_PREFIX must be an absolute non-root path")
        return normalized

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in allowed:
            raise ValueError(f"API_LOG_LEVEL must be one of {sorted(allowed)}")
        return normalized

    @field_validator("supported_locales")
    @classmethod
    def ensure_locales_are_unique(cls, value: list[Locale]) -> list[Locale]:
        if not value or len(value) != len(set(value)):
            raise ValueError("APP_SUPPORTED_LOCALES must be non-empty and unique")
        return value

    def model_post_init(self, __context: object) -> None:
        if self.default_locale not in self.supported_locales:
            raise ValueError("APP_DEFAULT_LOCALE must be included in APP_SUPPORTED_LOCALES")
        if self.app_env == "production" and "*" in self.allowed_hosts:
            raise ValueError("Wildcard API_ALLOWED_HOSTS is forbidden in production")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def media_root(self) -> Path:
        return self.storage_root / "media"

    @property
    def runtime_directories(self) -> tuple[Path, ...]:
        return (
            self.storage_root,
            self.media_root,
            self.backup_root,
            self.temp_root,
            self.log_root,
        )

    def telegram_token_value(self) -> str | None:
        return self.telegram_bot_token.get_secret_value() if self.telegram_bot_token else None

    def internal_api_key_value(self) -> str | None:
        return self.internal_api_key.get_secret_value() if self.internal_api_key else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
