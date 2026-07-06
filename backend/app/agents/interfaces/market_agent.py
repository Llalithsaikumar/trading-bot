"""IMarketAgent — contract for fetching raw market data from exchanges."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IMarketAgent(Protocol):
    """
    Structural interface for the Market Agent node.

    Implementations fetch OHLCV candles, ticker snapshots, and order books
    from the configured exchange via the injected ExchangeClient.
    """

    async def fetch_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Fetch OHLCV candles for a symbol.

        Returns:
            List of dicts: {timestamp, open, high, low, close, volume}
        """
        ...

    async def fetch_ticker(
        self,
        exchange: str,
        symbol: str,
    ) -> dict[str, Any]:
        """
        Fetch the latest ticker snapshot.

        Returns:
            Dict: {bid, ask, last, volume_24h, change_24h_pct, high_24h, low_24h}
        """
        ...

    async def fetch_order_book(
        self,
        exchange: str,
        symbol: str,
        depth: int = 20,
    ) -> dict[str, Any]:
        """
        Fetch the current order book.

        Returns:
            Dict: {bids: [[price, qty], …], asks: [[price, qty], …]}
        """
        ...
