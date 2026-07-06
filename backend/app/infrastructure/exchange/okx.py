"""OKX exchange adapter (spot + perps + options via unified account)."""
from __future__ import annotations

from typing import Any, Literal

import ccxt.async_support as ccxt

from app.core.config import settings

from .base import CCXTExchangeBase

MarketType = Literal["spot", "swap", "future", "option"]


class OKXExchange(CCXTExchangeBase):
    """
    OKX unified account adapter.
    OKX requires an API passphrase in addition to key/secret.
    market_type controls the default product line:
      'swap'   — USDT perpetuals (default)
      'spot'   — spot trading
      'future' — delivery futures
      'option' — options
    """

    @property
    def exchange_id(self) -> str:
        return "okx"

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        passphrase: str = "",
        demo: bool = False,
        market_type: MarketType = "swap",
    ) -> None:
        config: dict[str, Any] = {
            "apiKey": api_key,
            "secret": api_secret,
            "password": passphrase,  # OKX calls this a trading passphrase
            "options": {"defaultType": market_type},
            "enableRateLimit": True,
        }
        if demo:
            config["sandboxMode"] = True
        self._ccxt = ccxt.okx(config)

    @classmethod
    def from_settings(cls, market_type: MarketType = "swap") -> "OKXExchange":
        """Construct from application settings."""
        return cls(
            api_key=settings.OKX_API_KEY,
            api_secret=settings.OKX_API_SECRET,
            passphrase=settings.OKX_PASSPHRASE,
            demo=settings.OKX_DEMO,
            market_type=market_type,
        )
