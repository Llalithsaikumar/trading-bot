"""
Abstract exchange interface and shared CCXT-backed implementation.

ExchangeBase   — pure ABC; every method is abstract.
CCXTExchangeBase — concrete shared CCXT implementation; subclasses set _ccxt.

Usage (WebSocket):
    async for ticker in exchange.watch_ticker("BTC/USDT"):
        process(ticker)
"""
from __future__ import annotations

import asyncio
import contextlib
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

import ccxt.async_support as ccxt

from app.core.exceptions import ExchangeError
from app.core.logging import logger

_WS_RECONNECT_SLEEP: float = 1.0


# ---------------------------------------------------------------------------
# Shared CCXT → domain error translator
# ---------------------------------------------------------------------------

@contextlib.asynccontextmanager
async def ccxt_error_handler(exchange_id: str, operation: str):
    """Translate CCXT exceptions into domain ExchangeErrors."""
    try:
        yield
    except ccxt.AuthenticationError as exc:
        raise ExchangeError(str(exc), code="AUTH_ERROR") from exc
    except ccxt.InsufficientFunds as exc:
        raise ExchangeError(str(exc), code="INSUFFICIENT_FUNDS") from exc
    except ccxt.InvalidOrder as exc:
        raise ExchangeError(str(exc), code="INVALID_ORDER") from exc
    except ccxt.OrderNotFound as exc:
        raise ExchangeError(str(exc), code="ORDER_NOT_FOUND") from exc
    except ccxt.NetworkError as exc:
        raise ExchangeError(str(exc), code="NETWORK_ERROR") from exc
    except ccxt.ExchangeNotAvailable as exc:
        raise ExchangeError(str(exc), code="EXCHANGE_UNAVAILABLE") from exc
    except ccxt.BaseError as exc:
        raise ExchangeError(f"[{exchange_id}] {operation}: {exc}") from exc


# ---------------------------------------------------------------------------
# Pure abstract interface
# ---------------------------------------------------------------------------

class ExchangeBase(ABC):
    """
    Pure abstract interface every exchange adapter must satisfy.

    REST methods return CCXT-normalised dicts.
    WebSocket methods are async generators — iterate with `async for`.
    """

    @property
    @abstractmethod
    def exchange_id(self) -> str:
        """CCXT exchange identifier, e.g. 'binance' or 'bybit'."""

    # ── REST ────────────────────────────────────────────────────────────────────

    @abstractmethod
    async def fetch_balance(self) -> dict[str, Any]:
        """Return account balances (total, free, used per asset)."""

    @abstractmethod
    async def fetch_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """Return open positions. Pass symbol to restrict to one market."""

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
        since: int | None = None,
    ) -> list[list[Any]]:
        """Return OHLCV candles: [[timestamp_ms, O, H, L, C, volume], ...]."""

    @abstractmethod
    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Place a market order. side: 'buy' | 'sell'."""

    @abstractmethod
    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Place a limit order."""

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> dict[str, Any]:
        """Cancel an open order by its exchange-issued ID."""

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        """Return the latest ticker snapshot for a symbol."""

    @abstractmethod
    async def fetch_order_book(self, symbol: str, limit: int = 20) -> dict[str, Any]:
        """Return current bids/asks for a symbol."""

    @abstractmethod
    async def fetch_funding_rate(self, symbol: str) -> dict[str, Any]:
        """Return the current funding rate for a perpetual contract."""

    @abstractmethod
    async def fetch_funding_rates(
        self, symbols: list[str] | None = None
    ) -> dict[str, Any]:
        """Return funding rates for multiple perpetual contracts."""

    # ── WebSocket async generators ──────────────────────────────────────────────

    @abstractmethod
    async def watch_ticker(self, symbol: str) -> AsyncIterator[dict[str, Any]]:
        """Yield live ticker updates. Usage: `async for t in ex.watch_ticker(sym):`"""
        raise NotImplementedError

    @abstractmethod
    async def watch_ohlcv(
        self, symbol: str, timeframe: str = "1m"
    ) -> AsyncIterator[list[list[Any]]]:
        """Yield the latest OHLCV candle list on every new candle."""
        raise NotImplementedError

    @abstractmethod
    async def watch_order_book(
        self, symbol: str, limit: int = 20
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield order book snapshots on each update."""
        raise NotImplementedError

    @abstractmethod
    async def watch_trades(self, symbol: str) -> AsyncIterator[list[dict[str, Any]]]:
        """Yield batches of recent public trades on each new trade."""
        raise NotImplementedError

    @abstractmethod
    async def watch_balance(self) -> AsyncIterator[dict[str, Any]]:
        """Yield account balance snapshots on every change (authenticated)."""
        raise NotImplementedError

    @abstractmethod
    async def watch_orders(
        self, symbol: str | None = None
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Yield order-status updates (authenticated)."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close all WebSocket connections and HTTP sessions."""


# ---------------------------------------------------------------------------
# Shared CCXT implementation — subclasses provide exchange_id + set _ccxt
# ---------------------------------------------------------------------------

class CCXTExchangeBase(ExchangeBase, ABC):
    """
    Shared CCXT implementation of ExchangeBase.
    Concrete adapters set `self._ccxt` in `__init__` and declare `exchange_id`.
    WebSocket generators auto-reconnect on transient NetworkError.
    """

    _ccxt: ccxt.Exchange

    # ── REST ────────────────────────────────────────────────────────────────────

    async def fetch_balance(self) -> dict[str, Any]:
        async with ccxt_error_handler(self.exchange_id, "fetch_balance"):
            return await self._ccxt.fetch_balance()

    async def fetch_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        async with ccxt_error_handler(self.exchange_id, "fetch_positions"):
            return await self._ccxt.fetch_positions([symbol] if symbol else None)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
        since: int | None = None,
    ) -> list[list[Any]]:
        async with ccxt_error_handler(self.exchange_id, "fetch_ohlcv"):
            return await self._ccxt.fetch_ohlcv(
                symbol, timeframe, since=since, limit=limit
            )

    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with ccxt_error_handler(self.exchange_id, "create_market_order"):
            return await self._ccxt.create_market_order(
                symbol, side, amount, params=params or {}
            )

    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with ccxt_error_handler(self.exchange_id, "create_limit_order"):
            return await self._ccxt.create_limit_order(
                symbol, side, amount, price, params=params or {}
            )

    async def cancel_order(self, order_id: str, symbol: str) -> dict[str, Any]:
        async with ccxt_error_handler(self.exchange_id, "cancel_order"):
            return await self._ccxt.cancel_order(order_id, symbol)

    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        async with ccxt_error_handler(self.exchange_id, "fetch_ticker"):
            return await self._ccxt.fetch_ticker(symbol)

    async def fetch_order_book(self, symbol: str, limit: int = 20) -> dict[str, Any]:
        async with ccxt_error_handler(self.exchange_id, "fetch_order_book"):
            return await self._ccxt.fetch_order_book(symbol, limit)

    async def fetch_funding_rate(self, symbol: str) -> dict[str, Any]:
        async with ccxt_error_handler(self.exchange_id, "fetch_funding_rate"):
            return await self._ccxt.fetch_funding_rate(symbol)

    async def fetch_funding_rates(
        self, symbols: list[str] | None = None
    ) -> dict[str, Any]:
        async with ccxt_error_handler(self.exchange_id, "fetch_funding_rates"):
            return await self._ccxt.fetch_funding_rates(symbols)

    # ── WebSocket async generators ──────────────────────────────────────────────

    async def watch_ticker(self, symbol: str):  # type: ignore[override]
        while True:
            try:
                yield await self._ccxt.watch_ticker(symbol)
            except ccxt.NetworkError:
                logger.warning(
                    "watch_ticker reconnecting",
                    exchange=self.exchange_id,
                    symbol=symbol,
                )
                await asyncio.sleep(_WS_RECONNECT_SLEEP)
            except ccxt.BaseError as exc:
                raise ExchangeError(str(exc), code="WS_ERROR") from exc

    async def watch_ohlcv(self, symbol: str, timeframe: str = "1m"):  # type: ignore[override]
        while True:
            try:
                yield await self._ccxt.watch_ohlcv(symbol, timeframe)
            except ccxt.NetworkError:
                logger.warning(
                    "watch_ohlcv reconnecting",
                    exchange=self.exchange_id,
                    symbol=symbol,
                )
                await asyncio.sleep(_WS_RECONNECT_SLEEP)
            except ccxt.BaseError as exc:
                raise ExchangeError(str(exc), code="WS_ERROR") from exc

    async def watch_order_book(self, symbol: str, limit: int = 20):  # type: ignore[override]
        while True:
            try:
                yield await self._ccxt.watch_order_book(symbol, limit)
            except ccxt.NetworkError:
                logger.warning(
                    "watch_order_book reconnecting",
                    exchange=self.exchange_id,
                    symbol=symbol,
                )
                await asyncio.sleep(_WS_RECONNECT_SLEEP)
            except ccxt.BaseError as exc:
                raise ExchangeError(str(exc), code="WS_ERROR") from exc

    async def watch_trades(self, symbol: str):  # type: ignore[override]
        while True:
            try:
                yield await self._ccxt.watch_trades(symbol)
            except ccxt.NetworkError:
                logger.warning(
                    "watch_trades reconnecting",
                    exchange=self.exchange_id,
                    symbol=symbol,
                )
                await asyncio.sleep(_WS_RECONNECT_SLEEP)
            except ccxt.BaseError as exc:
                raise ExchangeError(str(exc), code="WS_ERROR") from exc

    async def watch_balance(self):  # type: ignore[override]
        while True:
            try:
                yield await self._ccxt.watch_balance()
            except ccxt.NetworkError:
                logger.warning(
                    "watch_balance reconnecting", exchange=self.exchange_id
                )
                await asyncio.sleep(_WS_RECONNECT_SLEEP)
            except ccxt.BaseError as exc:
                raise ExchangeError(str(exc), code="WS_ERROR") from exc

    async def watch_orders(self, symbol: str | None = None):  # type: ignore[override]
        while True:
            try:
                yield await self._ccxt.watch_orders(symbol)
            except ccxt.NetworkError:
                logger.warning(
                    "watch_orders reconnecting", exchange=self.exchange_id
                )
                await asyncio.sleep(_WS_RECONNECT_SLEEP)
            except ccxt.BaseError as exc:
                raise ExchangeError(str(exc), code="WS_ERROR") from exc

    async def close(self) -> None:
        await self._ccxt.close()
        logger.info("Exchange connection closed", exchange=self.exchange_id)
