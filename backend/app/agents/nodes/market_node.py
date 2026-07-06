"""
Market Agent node — fetches, persists, and streams ticker, OHLCV, and order book snapshots.
Uses Binance WebSocket when possible, with automated fallback to REST polling.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, AsyncIterator

import ccxt
from loguru import logger
from sqlalchemy import select

from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.domain.models.market_data import OHLCV, MarketTicker, OrderBookSnapshot
from app.infrastructure.messaging.websocket_manager import ws_manager
from app.services.market_data.market_data_service import MarketDataService

if TYPE_CHECKING:
    from app.agents.graph.state import TradingState


class MarketAgent(BaseAgent):
    """
    Implements IMarketAgent.
    Graph position: second (after MemoryAgent).
    Populates: state.ohlcv, state.tickers, state.order_book
    Also supports real-time streaming via Binance WebSockets with REST fallback.
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)
        self._market_service = None
        if self._deps.session:
            self._market_service = MarketDataService(self._deps.session)
        self._replay_timestamp = None

    async def run(self, state: TradingState) -> dict[str, Any]:
        if state.ohlcv and state.tickers and state.order_book:
            self._log_info("market data already fetched, skipping for idempotency")
            return {
                "ohlcv": state.ohlcv,
                "tickers": state.tickers,
                "order_book": state.order_book,
            }

        self._log_info(
            "fetching market data",
            exchange=state.exchange,
            symbols=state.symbols,
            timeframe=state.timeframe,
        )
        try:

            self._replay_timestamp = await self._get_replay_timestamp(state)
            if self._replay_timestamp:
                self._log_info("running in historical replay mode", replay_time=self._replay_timestamp.isoformat())

            ohlcv: dict[str, list[dict[str, Any]]] = {}
            tickers: dict[str, dict[str, Any]] = {}
            order_book: dict[str, dict[str, Any]] = {}

            for symbol in state.symbols:
                # 1. Fetch Ticker & OHLCV
                if self._replay_timestamp:
                    tickers[symbol] = await self.fetch_ticker(state.exchange, symbol)
                    ohlcv[symbol] = await self.fetch_ohlcv(
                        state.exchange, symbol, state.timeframe
                    )
                else:
                    if self._market_service:
                        ticker_resp = await self._market_service.get_ticker(state.exchange, symbol)
                        tickers[symbol] = {
                            "bid": float(ticker_resp.bid),
                            "ask": float(ticker_resp.ask),
                            "last": float(ticker_resp.last),
                            "volume_24h": float(ticker_resp.volume_24h),
                            "change_24h_pct": float(ticker_resp.change_24h_pct or 0.0),
                        }

                        ohlcv_resp = await self._market_service.get_ohlcv(
                            state.exchange, symbol, state.timeframe
                        )
                        ohlcv[symbol] = [
                            {
                                "timestamp": c.timestamp,
                                "open": float(c.open),
                                "high": float(c.high),
                                "low": float(c.low),
                                "close": float(c.close),
                                "volume": float(c.volume),
                            }
                            for c in ohlcv_resp
                        ]
                    else:
                        tickers[symbol] = await self.fetch_ticker(state.exchange, symbol)
                        ohlcv[symbol] = await self.fetch_ohlcv(
                            state.exchange, symbol, state.timeframe
                        )

                # 2. Fetch & Store Order Book Snapshot
                ob_data = await self.fetch_order_book(state.exchange, symbol)
                order_book[symbol] = ob_data

                # Persist order book snapshot to PostgreSQL (live mode only)
                if self._deps.session and not self._replay_timestamp:
                    snapshot = OrderBookSnapshot(
                        exchange=state.exchange,
                        symbol=symbol,
                        timestamp=datetime.now(UTC),
                        bids=ob_data["bids"],
                        asks=ob_data["asks"],
                    )
                    self._deps.session.add(snapshot)
                    await self._deps.session.flush()

                # 3. Broadcast updates over WebSocket (live mode only)
                if not self._replay_timestamp:
                    await self._broadcast_ticker(state.exchange, symbol, tickers.get(symbol, {}))
                    await self._broadcast_orderbook(state.exchange, symbol, ob_data)

            self._log_info(
                "market data fetched and stored",
                symbols_count=len(state.symbols),
            )
            return {"ohlcv": ohlcv, "tickers": tickers, "order_book": order_book}
        except Exception as exc:
            return self._node_error(state, exc)

    # ── Real-Time Streaming & Fallback ──────────────────────────────────────────

    async def listen_live(
        self,
        symbols: list[str],
        timeframe: str = "1m",
        poll_interval: float = 3.0,
    ) -> None:
        """
        Subscribe to live updates via WebSocket where supported, falling back
        to periodic REST polling loop on failure or unsupported client.
        """
        exc = self._deps.exchange
        if not exc:
            logger.error("No exchange client available for live streaming")
            return

        # Attempt WebSocket connection by watching streams
        try:
            tasks = []
            for symbol in symbols:
                tasks.append(asyncio.create_task(self._watch_ticker_stream(exc, symbol)))
                tasks.append(asyncio.create_task(self._watch_orderbook_stream(exc, symbol)))
                tasks.append(
                    asyncio.create_task(self._watch_ohlcv_stream(exc, symbol, timeframe))
                )

            logger.info("Started CCXT Pro WebSocket streams", exchange=exc.exchange_id, symbols=symbols)
            await asyncio.gather(*tasks)
        except (AttributeError, NotImplementedError, ccxt.NotSupported) as exc_ws:
            logger.warning(
                "WebSocket watch methods not supported by exchange client. Falling back to REST polling loop.",
                exchange=exc.exchange_id,
                error=str(exc_ws),
            )
            await self._run_rest_fallback_loop(exc, symbols, timeframe, poll_interval)
        except Exception as e:
            logger.error("WebSocket subscription error, falling back to REST", error=str(e))
            await self._run_rest_fallback_loop(exc, symbols, timeframe, poll_interval)

    async def _watch_ticker_stream(self, exc: Any, symbol: str) -> None:
        async for raw_ticker in exc.watch_ticker(symbol):
            ticker_data = {
                "bid": float(raw_ticker.get("bid") or 0.0),
                "ask": float(raw_ticker.get("ask") or 0.0),
                "last": float(raw_ticker.get("last") or raw_ticker.get("close") or 0.0),
                "volume_24h": float(raw_ticker.get("baseVolume") or raw_ticker.get("volume") or 0.0),
                "change_24h_pct": float(raw_ticker.get("percentage") or 0.0),
            }
            # Persist to DB if session exists
            if self._deps.session and self._market_service:
                await self._market_service.sync_ticker(exc.exchange_id, symbol)
            # Broadcast
            await self._broadcast_ticker(exc.exchange_id, symbol, ticker_data)

    async def _watch_orderbook_stream(self, exc: Any, symbol: str) -> None:
        async for raw_ob in exc.watch_order_book(symbol, 20):
            ob_data = {
                "bids": [[float(b[0]), float(b[1])] for b in raw_ob.get("bids", [])[:20]],
                "asks": [[float(a[0]), float(a[1])] for a in raw_ob.get("asks", [])[:20]],
            }
            # Persist to DB
            if self._deps.session:
                snapshot = OrderBookSnapshot(
                    exchange=exc.exchange_id,
                    symbol=symbol,
                    timestamp=datetime.now(UTC),
                    bids=ob_data["bids"],
                    asks=ob_data["asks"],
                )
                self._deps.session.add(snapshot)
                await self._deps.session.flush()
            # Broadcast
            await self._broadcast_orderbook(exc.exchange_id, symbol, ob_data)

    async def _watch_ohlcv_stream(self, exc: Any, symbol: str, timeframe: str) -> None:
        async for raw_candles in exc.watch_ohlcv(symbol, timeframe):
            # Persist
            if self._deps.session and self._market_service:
                await self._market_service.get_ohlcv(exc.exchange_id, symbol, timeframe, limit=100)

    async def _run_rest_fallback_loop(
        self,
        exc: Any,
        symbols: list[str],
        timeframe: str,
        interval: float,
    ) -> None:
        """Periodic REST polling fallback."""
        logger.info(
            "Starting REST polling loop",
            exchange=exc.exchange_id,
            symbols=symbols,
            interval=interval,
        )
        while True:
            for symbol in symbols:
                try:
                    # Sync ticker & OHLCV via service (performs postgres updates)
                    if self._market_service:
                        ticker_resp = await self._market_service.sync_ticker(exc.exchange_id, symbol)
                        ticker_data = {
                            "bid": float(ticker_resp.bid),
                            "ask": float(ticker_resp.ask),
                            "last": float(ticker_resp.last),
                            "volume_24h": float(ticker_resp.volume_24h),
                            "change_24h_pct": float(ticker_resp.change_24h_pct or 0.0),
                        }
                        await self._broadcast_ticker(exc.exchange_id, symbol, ticker_data)

                        await self._market_service.get_ohlcv(exc.exchange_id, symbol, timeframe)

                    # Order Book
                    ob_data = await self.fetch_order_book(exc.exchange_id, symbol)
                    if self._deps.session:
                        snapshot = OrderBookSnapshot(
                            exchange=exc.exchange_id,
                            symbol=symbol,
                            timestamp=datetime.now(UTC),
                            bids=ob_data["bids"],
                            asks=ob_data["asks"],
                        )
                        self._deps.session.add(snapshot)
                        await self._deps.session.flush()

                    await self._broadcast_orderbook(exc.exchange_id, symbol, ob_data)
                except Exception as e:
                    logger.error("REST polling tick failure", symbol=symbol, error=str(e))

            await asyncio.sleep(interval)

    # ── Helpers & Broadcasting ──────────────────────────────────────────────────

    async def _broadcast_ticker(self, exchange: str, symbol: str, ticker: dict[str, Any]) -> None:
        channel = f"ticker:{exchange}:{symbol}"
        await ws_manager.broadcast_channel(
            channel,
            {
                "type": "ticker_update",
                "channel": channel,
                "payload": ticker,
                "timestamp": str(datetime.now(UTC)),
            },
        )

    async def _broadcast_orderbook(self, exchange: str, symbol: str, ob: dict[str, Any]) -> None:
        channel = f"orderbook:{exchange}:{symbol}"
        await ws_manager.broadcast_channel(
            channel,
            {
                "type": "orderbook_update",
                "channel": channel,
                "payload": ob,
                "timestamp": str(datetime.now(UTC)),
            },
        )

    # ── IMarketAgent Implementation with caching, retries & replay ─────────────

    async def fetch_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        # 1. Historical Replay
        if self._replay_timestamp:
            return await self._fetch_ohlcv_replay(exchange, symbol, timeframe, limit)

        # 2. Redis Caching
        cache_key = f"market:ohlcv:{exchange}:{symbol}:{timeframe}:{limit}"
        cached = await self._get_cache(cache_key)
        if cached is not None:
            return cached

        # 3. Exchange Fetch with Retries
        if self._deps.exchange is None:
            return []
        raw = await self._execute_with_retry(
            self._deps.exchange.fetch_ohlcv, symbol, timeframe, limit=limit
        )
        res = [
            {
                "timestamp": str(c[0]),
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[5]),
            }
            for c in raw
        ]
        await self._set_cache(cache_key, res, ttl=30)
        return res

    async def fetch_ticker(
        self,
        exchange: str,
        symbol: str,
    ) -> dict[str, Any]:
        # 1. Historical Replay
        if self._replay_timestamp:
            return await self._fetch_ticker_replay(exchange, symbol)

        # 2. Redis Caching
        cache_key = f"market:ticker:{exchange}:{symbol}"
        cached = await self._get_cache(cache_key)
        if cached is not None:
            return cached

        # 3. Exchange Fetch with Retries
        if self._deps.exchange is None:
            return {}
        raw = await self._execute_with_retry(self._deps.exchange.fetch_ticker, symbol)
        res = {
            "bid": float(raw.get("bid") or 0.0),
            "ask": float(raw.get("ask") or 0.0),
            "last": float(raw.get("last") or raw.get("close") or 0.0),
            "volume_24h": float(raw.get("baseVolume") or raw.get("volume") or 0.0),
            "change_24h_pct": float(raw.get("percentage") or 0.0),
        }
        await self._set_cache(cache_key, res, ttl=5)
        return res

    async def fetch_order_book(
        self,
        exchange: str,
        symbol: str,
        depth: int = 20,
    ) -> dict[str, Any]:
        # 1. Historical Replay
        if self._replay_timestamp:
            return await self._fetch_order_book_replay(exchange, symbol, depth)

        # 2. Redis Caching
        cache_key = f"market:orderbook:{exchange}:{symbol}:{depth}"
        cached = await self._get_cache(cache_key)
        if cached is not None:
            return cached

        # 3. Exchange Fetch with Retries
        if self._deps.exchange is None:
            return {}
        raw = await self._execute_with_retry(
            self._deps.exchange.fetch_order_book, symbol, limit=depth
        )
        res = {
            "bids": [[float(b[0]), float(b[1])] for b in raw.get("bids", [])[:depth]],
            "asks": [[float(a[0]), float(a[1])] for a in raw.get("asks", [])[:depth]],
        }
        await self._set_cache(cache_key, res, ttl=2)
        return res

    # ── Replay Helpers ─────────────────────────────────────────────────────────

    async def _fetch_ohlcv_replay(
        self, exchange: str, symbol: str, timeframe: str, limit: int
    ) -> list[dict[str, Any]]:
        if not self._deps.session:
            return []
        stmt = (
            select(OHLCV)
            .where(
                OHLCV.exchange == exchange,
                OHLCV.symbol == symbol,
                OHLCV.timeframe == timeframe,
                OHLCV.timestamp <= self._replay_timestamp,
            )
            .order_by(OHLCV.timestamp.desc())
            .limit(limit)
        )
        res = await self._deps.session.execute(stmt)
        candles = res.scalars().all()
        return [
            {
                "timestamp": str(int(c.timestamp.timestamp() * 1000)),
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(c.volume),
            }
            for c in reversed(candles)
        ]

    async def _fetch_ticker_replay(self, exchange: str, symbol: str) -> dict[str, Any]:
        candles = await self._fetch_ohlcv_replay(exchange, symbol, "1m", limit=1)
        if not candles:
            # Try getting default timeframe from state or standard settings
            candles = await self._fetch_ohlcv_replay(exchange, symbol, "1h", limit=1)
        if candles:
            latest = candles[-1]
            last_price = float(latest["close"])
            volume = float(latest["volume"])
            return {
                "bid": last_price,
                "ask": last_price,
                "last": last_price,
                "volume_24h": volume,
                "change_24h_pct": 0.0,
            }
        return {}

    async def _fetch_order_book_replay(
        self, exchange: str, symbol: str, depth: int
    ) -> dict[str, Any]:
        if not self._deps.session:
            return {"bids": [], "asks": []}
        stmt = (
            select(OrderBookSnapshot)
            .where(
                OrderBookSnapshot.exchange == exchange,
                OrderBookSnapshot.symbol == symbol,
                OrderBookSnapshot.timestamp <= self._replay_timestamp,
            )
            .order_by(OrderBookSnapshot.timestamp.desc())
            .limit(1)
        )
        res = await self._deps.session.execute(stmt)
        snap = res.scalar_one_or_none()
        if snap:
            return {
                "bids": snap.bids[:depth],
                "asks": snap.asks[:depth],
            }
        return {"bids": [], "asks": []}

    # ── Utilities ──────────────────────────────────────────────────────────────

    async def _get_replay_timestamp(self, state: Any | None) -> datetime | None:
        if state and hasattr(state, "node_errors") and state.node_errors and "replay_timestamp" in state.node_errors:
            try:
                import arrow
                return arrow.get(state.node_errors["replay_timestamp"]).datetime
            except Exception:
                pass

        if self._deps.session and state and hasattr(state, "strategy_id") and state.strategy_id:
            try:
                import uuid
                from app.domain.models.strategy import Strategy
                strategy = await self._deps.session.get(Strategy, uuid.UUID(state.strategy_id))
                if strategy and strategy.config and "replay_timestamp" in strategy.config:
                    import arrow
                    return arrow.get(strategy.config["replay_timestamp"]).datetime
            except Exception:
                pass
        return None

    async def _get_cache(self, key: str) -> Any | None:
        if self._deps.redis:
            try:
                import json
                val = await self._deps.redis.get(key)
                if val:
                    return json.loads(val)
            except Exception:
                pass
        return None

    async def _set_cache(self, key: str, value: Any, ttl: int) -> None:
        if self._deps.redis:
            try:
                import json
                await self._deps.redis.set(key, json.dumps(value), ex=ttl)
            except Exception:
                pass

    async def _execute_with_retry(self, operation: Any, *args: Any, **kwargs: Any) -> Any:
        attempts = 3
        delay = 0.5
        for attempt in range(attempts):
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation(*args, **kwargs)
                else:
                    return operation(*args, **kwargs)
            except Exception as exc:
                # Catch transient network or retryable errors
                import ccxt
                if not isinstance(exc, (ccxt.NetworkError, ccxt.RequestTimeout, asyncio.TimeoutError)):
                    raise
                if attempt == attempts - 1:
                    raise
                self._log_warning(
                    "transient exchange error, retrying",
                    attempt=attempt + 1,
                    error=str(exc),
                )
                await asyncio.sleep(delay)
                delay *= 2
        raise RuntimeError("Retry loop exhausted")

