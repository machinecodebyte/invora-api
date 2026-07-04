import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_async_database_session_smoke() -> None:
    from app.db.session import AsyncSessionLocal, check_database_ready

    if not await check_database_ready():
        pytest.skip("Test database is not available.")

    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))

    assert result.scalar_one() == 1
