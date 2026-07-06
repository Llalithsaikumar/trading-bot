"""
Async SQLAlchemy engine and session factory.
Provides get_db() dependency for FastAPI route handlers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,  # detect stale connections
    pool_recycle=3600,  # recycle connections after 1 hour
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------
# Alias used by Celery background tasks (sync context can't use the FastAPI dependency)
AsyncSessionLocal = AsyncSessionFactory


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency: yield an async DB session."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
