import pytest
from pydantic import ValidationError

from app.core.config import get_settings


def test_config_loads_required_settings(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_NAME", "Invora Backend Test")
    monkeypatch.setenv("APP_TAGLINE", "Predict - Optimize - Replenish")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("API_V1_PREFIX", "/api/v1/")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/invora_test",
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:56379/1")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    monkeypatch.setenv("LOG_LEVEL", "info")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-foundation")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "45")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")

    settings = get_settings()

    assert settings.APP_NAME == "Invora Backend Test"
    assert settings.APP_TAGLINE == "Predict - Optimize - Replenish"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.LOG_LEVEL == "INFO"
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    get_settings.cache_clear()


def test_app_imports() -> None:
    from app.main import app

    assert app.title


def test_config_rejects_wildcard_cors_with_credentials(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(ValidationError, match="CORS_ORIGINS cannot use wildcard"):
        get_settings()

    get_settings.cache_clear()


@pytest.mark.parametrize(
    ("database_url", "expected_url"),
    [
        (
            "postgres://postgres:postgres@localhost:5432/invora",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/invora",
        ),
        (
            "postgres+asyncpg://postgres:postgres@localhost:5432/invora",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/invora",
        ),
        (
            "postgresql://postgres:postgres@localhost:5432/invora",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/invora",
        ),
    ],
)
def test_config_normalizes_postgresql_dialects(
    monkeypatch,
    database_url,
    expected_url,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", database_url)

    assert get_settings().DATABASE_URL == expected_url

    get_settings.cache_clear()


def test_config_rejects_non_postgresql_database_urls(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///invora.db")

    with pytest.raises(ValidationError, match="DATABASE_URL must use"):
        get_settings()

    get_settings.cache_clear()


def test_config_treats_release_debug_as_disabled(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("DEBUG", "release")

    assert get_settings().DEBUG is False

    get_settings.cache_clear()


def test_config_rejects_production_debug(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "true")

    with pytest.raises(ValidationError, match="DEBUG must be false"):
        get_settings()

    get_settings.cache_clear()
