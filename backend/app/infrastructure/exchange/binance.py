"""Binance exchange adapter (spot + USDT-M perps + COIN-M futures)."""
from __future__ import annotations

from typing import Any, Literal

import ccxt.async_support as ccxt

from app.core.config import settings

from .base import CCXTExchangeBase

MarketType = Literal["spot", "future", "swap", "margin"]


class BinanceExchange(CCXTExchangeBase):
    """
    Binance adapter.
    market_type controls which product line is used by default:
      'spot'   — spot trading (default)
      'swap'   — USDT-M perpetual contracts
      'future' — COIN-M delivery futures
    """

    @property
    def exchange_id(self) -> str:
        return "binance"

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = False,
        market_type: MarketType = "spot",
    ) -> None:
        config: dict[str, Any] = {
            "apiKey": api_key,
            "secret": api_secret,
            "options": {"defaultType": market_type},
            "enableRateLimit": True,
        }
        if testnet:
            config["sandboxMode"] = True
        self._ccxt = ccxt.binance(config)

    @classmethod
    def from_settings(cls, market_type: MarketType = "spot") -> "BinanceExchange":
        """Construct from application settings."""
        return cls(
            api_key=settings.BINANCE_API_KEY,
            api_secret=settings.BINANCE_API_SECRET,
            testnet=settings.BINANCE_TESTNET,
            market_type=market_type,
        )
