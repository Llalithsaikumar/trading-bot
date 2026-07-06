"""Market data repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.domain.models.market_data import OHLCV, MarketTicker
from app.infrastructure.repositories.base import BaseRepository


class OHLCVRepository(BaseRepository[OHLCV]):
    model = OHLCV

    async def get_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[OHLCV]:
        stmt = select(OHLCV).where(
            OHLCV.exchange == exchange,
            OHLCV.symbol == symbol,
            OHLCV.timeframe == timeframe,
        )
        if since:
            stmt = stmt.where(OHLCV.timestamp >= since)
        stmt = stmt.order_by(OHLCV.timestamp.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class TickerRepository(BaseRepository[MarketTicker]):
    model = MarketTicker

    async def get_latest(self, exchange: str, symbol: str) -> MarketTicker | None:
        stmt = (
            select(MarketTicker)
            .where(MarketTicker.exchange == exchange, MarketTicker.symbol == symbol)
            .order_by(MarketTicker.timestamp.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
