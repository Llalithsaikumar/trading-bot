"""Polymarket snapshots repository."""

from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import select, desc

from app.domain.models.polymarket import PolymarketSnapshot
from app.infrastructure.repositories.base import BaseRepository

if TYPE_CHECKING:
    from datetime import datetime


class PolymarketRepository(BaseRepository[PolymarketSnapshot]):
    model = PolymarketSnapshot

    async def get_latest_snapshots(self, limit: int = 50) -> list[PolymarketSnapshot]:
        """Fetch the most recent batch of snapshots."""
        # Find the latest fetched_at timestamp
        latest_ts_stmt = (
            select(PolymarketSnapshot.fetched_at)
            .order_by(desc(PolymarketSnapshot.fetched_at))
            .limit(1)
        )
        latest_ts_res = await self._session.execute(latest_ts_stmt)
        latest_ts = latest_ts_res.scalar_one_or_none()

        if not latest_ts:
            return []

        # Get all snapshots from that batch
        stmt = (
            select(PolymarketSnapshot)
            .where(PolymarketSnapshot.fetched_at == latest_ts)
            .order_by(desc(PolymarketSnapshot.liquidity))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_condition_id(
        self, condition_id: str, limit: int = 20
    ) -> list[PolymarketSnapshot]:
        """Get history for a specific market."""
        stmt = (
            select(PolymarketSnapshot)
            .where(PolymarketSnapshot.condition_id == condition_id)
            .order_by(desc(PolymarketSnapshot.fetched_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
