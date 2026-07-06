"""
Market Agent node — fetches OHLCV, tickers, and order books.

Calls the exchange via the injected ExchangeClient and populates
ohlcv, tickers, and order_book in TradingState.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.agents.interfaces.base import AgentDependencies, BaseAgent

if TYPE_CHECKING:
    from app.agents.graph.state import TradingState


class MarketAgent(BaseAgent):
    """
    Implements IMarketAgent.

    Graph position: second (after MemoryAgent).
    Populates: state.ohlcv, state.tickers, state.order_book
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)

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
                ohlcv[symbol] = await self.fetch_ohlcv(state.exchange, symbol, state.timeframe)
                tickers[symbol] = await self.fetch_ticker(state.exchange, symbol)
                order_book[symbol] = await self.fetch_order_book(state.exchange, symbol)

            self._log_info(
                "market data fetched",
                symbols_count=len(state.symbols),
            )
            return {"ohlcv": ohlcv, "tickers": tickers, "order_book": order_book}
        except Exception as exc:
            return self._node_error(state, exc)

    # ── IMarketAgent implementation ───────────────────────────────────────────

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
