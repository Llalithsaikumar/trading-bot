"""Bybit exchange adapter (spot + perpetuals + options via V5 unified API)."""

from __future__ import annotations

from typing import Any, Literal

import ccxt.async_support as ccxt

from app.core.config import settings

from .base import CCXTExchangeBase

MarketType = Literal["spot", "swap", "future", "option"]


class BybitExchange(CCXTExchangeBase):
    """
    Bybit V5 unified adapter.
    market_type controls the default product line:
      'swap'   — USDT perpetuals (default)
      'spot'   — spot trading
      'future' — inverse/delivery futures
      'option' — options
    """

    @property
    def exchange_id(self) -> str:
        return "bybit"

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = False,
        market_type: MarketType = "swap",
    ) -> None:
        config: dict[str, Any] = {
            "apiKey": api_key,
            "secret": api_secret,
            "options": {"defaultType": market_type},
            "enableRateLimit": True,
        }
        if testnet:
            config["sandboxMode"] = True
        self._ccxt = ccxt.bybit(config)

    @classmethod
    def from_settings(cls, market_type: MarketType = "swap") -> BybitExchange:
        """Construct from application settings."""
        return cls(
            api_key=settings.BYBIT_API_KEY,
            api_secret=settings.BYBIT_API_SECRET,
            testnet=settings.BYBIT_TESTNET,
            market_type=market_type,
        )
