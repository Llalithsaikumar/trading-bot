"""
Generic async repository.
Concrete repositories extend this class and call super() methods.
"""
from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    CRUD base repository using SQLAlchemy async sessions.
    Extend and override methods as needed.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelT | None:
        result = await self._session.get(self.model, entity_id)
        return result

    async def get_all(
        self, offset: int = 0, limit: int = 20, **filters: Any
    ) -> tuple[list[ModelT], int]:
        """Returns (items, total_count)."""
        stmt = select(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def create(self, obj: ModelT) -> ModelT:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(
        self, entity_id: uuid.UUID, data: dict[str, Any]
    ) -> ModelT | None:
        stmt = (
            update(self.model)
            .where(self.model.id == entity_id)  # type: ignore[attr-defined]
            .values(**data)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, entity_id: uuid.UUID) -> bool:
        stmt = delete(self.model).where(self.model.id == entity_id)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def exists(self, **filters: Any) -> bool:
        stmt = select(func.count()).select_from(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        count = (await self._session.execute(stmt)).scalar_one()
        return count > 0
