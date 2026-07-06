"""
MarketDataService — fetch, cache, and serve market data.
Implements a read-through cache: Redis → Exchange.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schemas.market_data import OHLCVResponse, OrderBookResponse, TickerResponse


import json
from datetime import datetime, UTC
from decimal import Decimal

from sqlalchemy import select

from app.domain.models.market_data import OHLCV, MarketTicker
from app.domain.schemas.market_data import OHLCVResponse, OrderBookResponse, TickerResponse
from app.infrastructure.cache.redis_client import cache_get, cache_set
from app.infrastructure.exchange import get_exchange
from app.infrastructure.repositories.market_data_repository import OHLCVRepository, TickerRepository


class MarketDataService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_ticker(self, exchange: str, symbol: str) -> TickerResponse:
        """Return latest ticker, preferring Redis cache over live exchange call."""
        cache_key = f"ticker:{exchange}:{symbol}"
        cached = await cache_get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                return TickerResponse(
                    exchange=data["exchange"],
                    symbol=data["symbol"],
                    timestamp=data["timestamp"],
                    bid=Decimal(str(data["bid"])),
                    ask=Decimal(str(data["ask"])),
                    last=Decimal(str(data["last"])),
                    volume_24h=Decimal(str(data["volume_24h"])),
                    change_24h_pct=Decimal(str(data["change_24h_pct"]))
                    if data.get("change_24h_pct")
                    else None,
                    high_24h=Decimal(str(data["high_24h"])) if data.get("high_24h") else None,
                    low_24h=Decimal(str(data["low_24h"])) if data.get("low_24h") else None,
                    funding_rate=Decimal(str(data["funding_rate"]))
                    if data.get("funding_rate")
                    else None,
                )
            except Exception:
                pass

        return await self.sync_ticker(exchange, symbol)

    async def get_ohlcv(
        self, exchange: str, symbol: str, timeframe: str, limit: int = 100
    ) -> list[OHLCVResponse]:
        ohlcv_repo = OHLCVRepository(self._session)
        candles = await ohlcv_repo.get_candles(exchange, symbol, timeframe, limit=limit)

        # Check if we need to fetch live data (empty DB or latest candle is too old)
        need_fetch = False
        if not candles:
            need_fetch = True
        else:
            # Check age of the latest candle (first in the list since it is descending)
            latest_ts = candles[0].timestamp
            # Timeframe simple check: timeframe format is e.g. 1m, 5m, 1h, 1d
            # If current time is past latest_ts + some interval, fetch fresh
            val = int("".join([c for c in timeframe if c.isdigit()] or ["1"]))
            unit = "".join([c for c in timeframe if not c.isdigit()]).lower()
            delta_seconds = val * 60
            if unit == "h":
                delta_seconds = val * 3600
            elif unit == "d":
                delta_seconds = val * 86400

            if (datetime.now(UTC) - latest_ts).total_seconds() > delta_seconds:
                need_fetch = True

        if need_fetch:
            try:
                exc = get_exchange(exchange)
                live_candles = await exc.fetch_ohlcv(symbol, timeframe, limit=limit)

                # Check which candles already exist to avoid unique constraint error
                timestamps = [datetime.fromtimestamp(c[0] / 1000, tz=UTC) for c in live_candles]
                stmt = select(OHLCV.timestamp).where(
                    OHLCV.exchange == exchange,
                    OHLCV.symbol == symbol,
                    OHLCV.timeframe == timeframe,
                    OHLCV.timestamp.in_(timestamps),
                )
                result = await self._session.execute(stmt)
                existing_ts = set(result.scalars().all())

                for c in live_candles:
                    ts = datetime.fromtimestamp(c[0] / 1000, tz=UTC)
                    if ts not in existing_ts:
                        new_candle = OHLCV(
                            exchange=exchange,
                            symbol=symbol,
                            timeframe=timeframe,
                            timestamp=ts,
                            open=Decimal(str(c[1])),
                            high=Decimal(str(c[2])),
                            low=Decimal(str(c[3])),
                            close=Decimal(str(c[4])),
                            volume=Decimal(str(c[5])),
                        )
                        self._session.add(new_candle)

                await self._session.flush()
                # Query database again for updated candles
                candles = await ohlcv_repo.get_candles(exchange, symbol, timeframe, limit=limit)
            except Exception:
                # Fallback to whatever is in the database if exchange fetch fails
                pass

        candles.reverse()  # Return in chronological order
        return [
            OHLCVResponse(
                timestamp=str(int(c.timestamp.timestamp() * 1000)),
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
            )
            for c in candles
        ]

    async def get_order_book(
        self, exchange: str, symbol: str, depth: int = 20
    ) -> OrderBookResponse:
        cache_key = f"orderbook:{exchange}:{symbol}"
        cached = await cache_get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                return OrderBookResponse(
                    exchange=exchange,
                    symbol=symbol,
                    bids=[[Decimal(str(b[0])), Decimal(str(b[1]))] for b in data["bids"]],
                    asks=[[Decimal(str(a[0])), Decimal(str(a[1]))] for a in data["asks"]],
                    timestamp=data.get("timestamp", ""),
                )
            except Exception:
                pass

        exc = get_exchange(exchange)
        ob = await exc.fetch_order_book(symbol, limit=depth)

        bids = [[Decimal(str(b[0])), Decimal(str(b[1]))] for b in ob.get("bids", [])[:depth]]
        asks = [[Decimal(str(a[0])), Decimal(str(a[1]))] for a in ob.get("asks", [])[:depth]]
        ts = str(ob.get("timestamp") or "")

        cache_data = {
            "bids": [[str(b[0]), str(b[1])] for b in bids],
            "asks": [[str(a[0]), str(a[1])] for a in asks],
            "timestamp": ts,
        }
        await cache_set(cache_key, json.dumps(cache_data), ttl=5)

        return OrderBookResponse(
            exchange=exchange,
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=ts,
        )

    async def sync_ticker(self, exchange: str, symbol: str) -> TickerResponse:
        """Force-refresh a ticker from the exchange and update DB + cache."""
        exc = get_exchange(exchange)
        ticker = await exc.fetch_ticker(symbol)

        ticker_repo = TickerRepository(self._session)
        db_ticker = await ticker_repo.get_latest(exchange, symbol)
        ts = (
            datetime.fromtimestamp((ticker.get("timestamp") or 0) / 1000, tz=UTC)
            if ticker.get("timestamp")
            else datetime.now(UTC)
        )

        bid = Decimal(str(ticker.get("bid") or 0))
        ask = Decimal(str(ticker.get("ask") or 0))
        last = Decimal(str(ticker.get("last") or ticker.get("close") or 0))
        volume = Decimal(str(ticker.get("baseVolume") or ticker.get("volume") or 0))
        change = (
            Decimal(str(ticker.get("percentage") or 0))
            if ticker.get("percentage") is not None
            else None
        )
        high = Decimal(str(ticker.get("high") or 0)) if ticker.get("high") is not None else None
        low = Decimal(str(ticker.get("low") or 0)) if ticker.get("low") is not None else None

        if db_ticker is None:
            db_ticker = MarketTicker(
                exchange=exchange,
                symbol=symbol,
                timestamp=ts,
                bid=bid,
                ask=ask,
                last=last,
                volume_24h=volume,
                change_24h_pct=change,
                high_24h=high,
                low_24h=low,
            )
            self._session.add(db_ticker)
        else:
            db_ticker.timestamp = ts
            db_ticker.bid = bid
            db_ticker.ask = ask
            db_ticker.last = last
            db_ticker.volume_24h = volume
            db_ticker.change_24h_pct = change
            db_ticker.high_24h = high
            db_ticker.low_24h = low
            self._session.add(db_ticker)

        await self._session.flush()

        response_data = {
            "exchange": exchange,
            "symbol": symbol,
            "timestamp": str(ticker.get("timestamp") or ""),
            "bid": str(db_ticker.bid),
            "ask": str(db_ticker.ask),
            "last": str(db_ticker.last),
            "volume_24h": str(db_ticker.volume_24h),
            "change_24h_pct": str(db_ticker.change_24h_pct)
            if db_ticker.change_24h_pct is not None
            else None,
            "high_24h": str(db_ticker.high_24h) if db_ticker.high_24h is not None else None,
            "low_24h": str(db_ticker.low_24h) if db_ticker.low_24h is not None else None,
            "funding_rate": None,
        }
        await cache_set(f"ticker:{exchange}:{symbol}", json.dumps(response_data), ttl=30)

        return TickerResponse(
            exchange=exchange,
            symbol=symbol,
            timestamp=response_data["timestamp"],
            bid=db_ticker.bid,
            ask=db_ticker.ask,
            last=db_ticker.last,
            volume_24h=db_ticker.volume_24h,
            change_24h_pct=db_ticker.change_24h_pct,
            high_24h=db_ticker.high_24h,
            low_24h=db_ticker.low_24h,
        )
