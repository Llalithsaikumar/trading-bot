"""ITechnicalAgent — contract for computing technical indicators."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ITechnicalAgent(Protocol):
    """
    Structural interface for the Technical Agent node.

    Implementations compute standard indicator bundles (RSI, MACD,
    Bollinger Bands, EMA, ATR) from OHLCV data and return a
    JSON-serialisable dict suitable for the Decision Agent's LLM prompt.
    """

    async def compute_indicators(
        self,
        symbol: str,
        ohlcv: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Compute all technical indicators for a single symbol.

        Args:
            symbol: Trading pair (e.g. "BTC/USDT").
            ohlcv:  Raw OHLCV list in CCXT format
                    [{timestamp, open, high, low, close, volume}, …].

        Returns:
            Dict with keys: rsi, macd, bollinger_bands, ema_20, ema_50, atr.
            Each value is a serialisable scalar or sub-dict.
        """
        ...

    async def compute_all(
        self,
        ohlcv_by_symbol: dict[str, list[dict[str, Any]]],
    ) -> dict[str, dict[str, Any]]:
        """
        Compute indicators for all symbols in the current state.

        Args:
            ohlcv_by_symbol: Mapping of symbol → OHLCV list.

        Returns:
            Mapping of symbol → indicator dict (same as compute_indicators).
        """
        ...
