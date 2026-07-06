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

    async def run(self, state: TradingState) -> dict[str, Any]:
        self._log_info(
            "fetching market data",
            exchange=state.exchange,
            symbols=state.symbols,
            timeframe=state.timeframe,
        )
        try:
            ohlcv: dict[str, list[dict[str, Any]]] = {}
            tickers: dict[str, dict[str, Any]] = {}
            order_book: dict[str, dict[str, Any]] = {}

            for symbol in state.symbols:
                # 1. Fetch Ticker & OHLCV via MarketDataService (which persists + caches)
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

                # 2. Fetch & Store Order Book Snapshot
                ob_data = await self.fetch_order_book(state.exchange, symbol)
                order_book[symbol] = ob_data

                # Persist order book snapshot to PostgreSQL
                if self._deps.session:
                    snapshot = OrderBookSnapshot(
                        exchange=state.exchange,
                        symbol=symbol,
                        timestamp=datetime.now(UTC),
                        bids=ob_data["bids"],
                        asks=ob_data["asks"],
                    )
                    self._deps.session.add(snapshot)
                    await self._deps.session.flush()

                # 3. Broadcast updates over WebSocket
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

    async def fetch_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if self._deps.exchange is None:
            return []
        raw = await self._deps.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        return [
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

    async def fetch_ticker(
        self,
        exchange: str,
        symbol: str,
    ) -> dict[str, Any]:
        if self._deps.exchange is None:
            return {}
        raw = await self._deps.exchange.fetch_ticker(symbol)
        return {
            "bid": float(raw.get("bid") or 0.0),
            "ask": float(raw.get("ask") or 0.0),
            "last": float(raw.get("last") or raw.get("close") or 0.0),
            "volume_24h": float(raw.get("baseVolume") or raw.get("volume") or 0.0),
            "change_24h_pct": float(raw.get("percentage") or 0.0),
        }

    async def fetch_order_book(
        self,
        exchange: str,
        symbol: str,
        depth: int = 20,
    ) -> dict[str, Any]:
        if self._deps.exchange is None:
            return {}
        raw = await self._deps.exchange.fetch_order_book(symbol, limit=depth)
        return {
            "bids": [[float(b[0]), float(b[1])] for b in raw.get("bids", [])[:depth]],
            "asks": [[float(a[0]), float(a[1])] for a in raw.get("asks", [])[:depth]],
        }
