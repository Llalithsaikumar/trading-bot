"""Long term memory database repository query engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.domain.models.memory import LongTermMemory
from app.infrastructure.repositories.base import BaseRepository

if TYPE_CHECKING:
    import uuid


class MemoryRepository(BaseRepository[LongTermMemory]):
    model = LongTermMemory

    async def search_semantic(
        self,
        strategy_id: uuid.UUID,
        query_vector: list[float],
        limit: int = 5,
    ) -> list[LongTermMemory]:
        """
        Perform semantic search for long-term memories using cosine distance.
        If using SQLite (testing), falls back to Python-based distance calculation.
        """
        if self._session.bind.dialect.name == "sqlite":
            stmt = select(LongTermMemory).where(LongTermMemory.strategy_id == strategy_id)
            result = await self._session.execute(stmt)
            memories = list(result.scalars().all())

            # Python-based fallback calculation
            import numpy as np

            def cosine_dist(v1: list[float], v2: list[float]) -> float:
                a = np.array(v1)
                b = np.array(v2)
                dot = np.dot(a, b)
                norm_a = np.linalg.norm(a)
                norm_b = np.linalg.norm(b)
                if norm_a == 0 or norm_b == 0:
                    return 1.0
                return float(1.0 - (dot / (norm_a * norm_b)))

            memories.sort(key=lambda m: cosine_dist(m.embedding, query_vector))
            return memories[:limit]

        # pgvector-native query
        stmt = (
            select(LongTermMemory)
            .where(LongTermMemory.strategy_id == strategy_id)
            .order_by(LongTermMemory.embedding.cosine_distance(query_vector))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
