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
    )

    assert settings.supported_locales == ["uz", "ru"]
    assert settings.allowed_hosts == ["localhost", "api"]
    assert settings.cors_origins == [
        "http://localhost:3000",
        "https://publisher.uboom.uz",
    ]


def test_default_locale_must_be_supported() -> None:
    with pytest.raises(ValidationError):
        Settings(default_locale="ru", supported_locales=["uz"])


def test_production_rejects_wildcard_hosts() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", allowed_hosts=["*"])


def test_api_prefix_and_log_level_are_validated() -> None:
    with pytest.raises(ValidationError):
        Settings(api_v1_prefix="api/v1")

    with pytest.raises(ValidationError):
        Settings(log_level="verbose")


def test_locale_configuration_rejects_duplicates_and_empty_values() -> None:
    with pytest.raises(ValidationError):
        Settings(supported_locales=["uz", "uz"])

    with pytest.raises(ValidationError):
        Settings(supported_locales=[])


def test_production_properties() -> None:
    settings = Settings(app_env="production", allowed_hosts=["publisher.uboom.uz"])

    assert settings.is_production is True
    assert len(settings.runtime_directories) == 4


def test_comma_separated_values_load_from_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("API_ALLOWED_HOSTS", "localhost,127.0.0.1,api")
    monkeypatch.setenv("APP_SUPPORTED_LOCALES", "uz,ru")

    settings = Settings()

    assert settings.allowed_hosts == ["localhost", "127.0.0.1", "api"]
    assert settings.supported_locales == ["uz", "ru"]
