from app.core.config import get_settings


def test_config_loads_required_settings(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_NAME", "Invora Backend Test")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("API_V1_PREFIX", "/api/v1/")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/invora_test",
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    monkeypatch.setenv("LOG_LEVEL", "info")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-foundation")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "45")

    settings = get_settings()

    assert settings.APP_NAME == "Invora Backend Test"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.LOG_LEVEL == "INFO"
    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    get_settings.cache_clear()


def test_app_imports() -> None:
    from app.main import app

    assert app.title
