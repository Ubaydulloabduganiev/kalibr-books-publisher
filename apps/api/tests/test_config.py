"""Configuration validation tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from kalibr_publisher.core.config import Settings


def test_csv_environment_values_are_normalized() -> None:
    settings = Settings(
        supported_locales=["uz", "ru"],
        allowed_hosts=["localhost", "api"],
        cors_origins=["http://localhost:3000", "https://publisher.uboom.uz"],
        _env_file=None,
    )

    assert settings.supported_locales == ["uz", "ru"]
    assert settings.allowed_hosts == ["localhost", "api"]
    assert settings.cors_origins == [
        "http://localhost:3000",
        "https://publisher.uboom.uz",
    ]


def test_default_locale_must_be_supported() -> None:
    with pytest.raises(ValidationError):
        Settings(default_locale="ru", supported_locales=["uz"], _env_file=None)


def test_production_rejects_wildcard_hosts() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", allowed_hosts=["*"], _env_file=None)


def test_api_prefix_and_log_level_are_validated() -> None:
    with pytest.raises(ValidationError):
        Settings(api_v1_prefix="api/v1", _env_file=None)

    with pytest.raises(ValidationError):
        Settings(log_level="verbose", _env_file=None)


def test_locale_configuration_rejects_duplicates_and_empty_values() -> None:
    with pytest.raises(ValidationError):
        Settings(supported_locales=["uz", "uz"], _env_file=None)

    with pytest.raises(ValidationError):
        Settings(supported_locales=[], _env_file=None)


def test_production_properties(tmp_path: Path) -> None:
    settings = Settings(
        app_env="production",
        allowed_hosts=["publisher.uboom.uz"],
        storage_root=tmp_path / "storage",
        backup_root=tmp_path / "backups",
        temp_root=tmp_path / "tmp",
        log_root=tmp_path / "logs",
        telegram_bot_token="123:abc",
        internal_api_key="secret",
        _env_file=None,
    )

    assert settings.is_production is True
    assert len(settings.runtime_directories) == 5
    assert settings.telegram_token_value() == "123:abc"
    assert settings.internal_api_key_value() == "secret"


def test_comma_separated_values_load_from_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("API_ALLOWED_HOSTS", "localhost,127.0.0.1,api")
    monkeypatch.setenv("APP_SUPPORTED_LOCALES", "uz,ru")

    settings = Settings(_env_file=None)

    assert settings.allowed_hosts == ["localhost", "127.0.0.1", "api"]
    assert settings.supported_locales == ["uz", "ru"]
