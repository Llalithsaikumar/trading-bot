"""Background tasks for fetching and storing market data."""

from __future__ import annotations

from celery import shared_task
from loguru import logger


import asyncio
from datetime import datetime, UTC
from sqlalchemy import select

from app.domain.enums.trading import StrategyStatus
from app.domain.models.strategy import Strategy
from app.infrastructure.database.session import AsyncSessionLocal


def _run(coro):
    """Run an async coroutine from a synchronous Celery worker."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _sync_market_data_async() -> dict:
    from app.infrastructure.messaging.websocket_manager import ws_manager
    from app.services.market_data.market_data_service import MarketDataService

    pairs = set()
    async with AsyncSessionLocal() as session:
        # 1. Get list of tracked symbols from DB
        stmt = select(Strategy).where(Strategy.status == StrategyStatus.ACTIVE)
        result = await session.execute(stmt)
        strategies = result.scalars().all()
        for strategy in strategies:
            for symbol in strategy.symbols:
                pairs.add((strategy.exchange, symbol))

        market_service = MarketDataService(session)
        sync_count = 0

        for exchange, symbol in pairs:
            try:
                # 2, 3, 4. Batch-fetch and cache in sync_ticker
                ticker_resp = await market_service.sync_ticker(exchange, symbol)
                sync_count += 1

                # 5. Broadcast via WebSocket
                channel = f"ticker:{exchange}:{symbol}"
                ws_data = {
                    "type": "ticker_update",
                    "channel": channel,
                    "payload": {
                        "last": str(ticker_resp.last),
                        "bid": str(ticker_resp.bid),
                        "ask": str(ticker_resp.ask),
                        "change_24h_pct": str(ticker_resp.change_24h_pct)
                        if ticker_resp.change_24h_pct is not None
                        else None,
                    },
                    "timestamp": ticker_resp.timestamp,
                }
                await ws_manager.broadcast_channel(channel, ws_data)
            except Exception as e:
                logger.error(f"Failed to sync ticker for {exchange}/{symbol}: {e}")

        await session.commit()
    return {"synced": sync_count}


async def _fetch_historical_ohlcv_async(
    exchange: str, symbol: str, timeframe: str, limit: int
) -> dict:
    from app.services.market_data.market_data_service import MarketDataService

    async with AsyncSessionLocal() as session:
        market_service = MarketDataService(session)
        candles = await market_service.get_ohlcv(exchange, symbol, timeframe, limit=limit)
        await session.commit()
    return {"count": len(candles)}


@shared_task(bind=True, name="app.workers.tasks.market_data_tasks.sync_market_data")
def sync_market_data(self) -> dict:
    """
    Fetch latest tickers for all tracked symbols and store in DB + Redis cache.
    Also broadcasts updates to WebSocket subscribers.
    """
    try:
        return _run(_sync_market_data_async())
    except Exception as exc:
        logger.error("sync_market_data failed", error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, name="app.workers.tasks.market_data_tasks.fetch_historical_ohlcv")
def fetch_historical_ohlcv(
    self, exchange: str, symbol: str, timeframe: str, limit: int = 500
) -> dict:
    """Backfill historical OHLCV data for a symbol."""
    try:
        return _run(_fetch_historical_ohlcv_async(exchange, symbol, timeframe, limit))
    except Exception as exc:
        logger.error("fetch_historical_ohlcv failed", error=str(exc))
        raise self.retry(exc=exc)
