"""
Pytest fixtures — shared across all test modules.
Provides an async test client, test DB session, and factories.
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("APP_SECRET_KEY", "test-app-secret")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test",
)

from app.domain.models.base import Base
from app.main import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# In-memory SQLite for unit tests (override with real PG in integration tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class MockRedis:
    def __init__(self) -> None:
        self.store: dict = {}

    async def get(self, key: str) -> Any:
        return self.store.get(key)

    async def set(self, key: str, value: Any, ex: Any = None) -> None:
        self.store[key] = value

    async def setex(self, key: str, ttl: int, value: Any) -> None:
        self.store[key] = value

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self.store.pop(key, None)

    async def ping(self) -> bool:
        return True

    async def lrange(self, key: str, start: int, stop: int) -> list:
        return []

    async def lpush(self, key: str, *values: Any) -> int:
        return len(values)

    async def ltrim(self, key: str, start: int, stop: int) -> None:
        pass

    async def expire(self, key: str, time: int) -> None:
        pass

    async def keys(self, pattern: str) -> list[str]:
        return list(self.store.keys())


@pytest.fixture(autouse=True)
def mock_redis_client(mocker):
    mock_instance = MockRedis()
    mocker.patch(
        "app.infrastructure.cache.redis_client.get_redis_client", return_value=mock_instance
    )
    return mock_instance


@pytest_asyncio.fixture(scope="function")
async def client(db_session) -> AsyncGenerator[AsyncClient]:
    from app.core.dependencies import get_db, get_redis

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: MockRedis()

    from httpx import ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
