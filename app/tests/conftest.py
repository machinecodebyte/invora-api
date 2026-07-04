import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient


def pytest_configure() -> None:
    os.environ["APP_NAME"] = "Invora Backend Test"
    os.environ["APP_ENV"] = "test"
    os.environ["DEBUG"] = "false"
    os.environ["API_V1_PREFIX"] = "/api/v1"
    os.environ["DATABASE_URL"] = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/invora_test"
    )
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:5173"
    os.environ["LOG_LEVEL"] = "WARNING"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-foundation"
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"


@pytest.fixture
def app():
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    return create_app()


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
