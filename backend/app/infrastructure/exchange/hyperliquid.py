"""
Hyperliquid exchange adapter.

Hyperliquid is a perpetuals-only DEX — no spot trading.
Authentication uses a wallet address + private key, not API key/secret.
Some bulk operations are not supported and are emulated by looping.
"""

from __future__ import annotations

from typing import Any

import ccxt.async_support as ccxt

from app.core.config import settings
from app.core.exceptions import ExchangeError

from .base import CCXTExchangeBase


class HyperliquidExchange(CCXTExchangeBase):
    """
    Hyperliquid DEX adapter.
    All markets are perpetuals — fetch_balance returns the perp account balance.
    """

    @property
    def exchange_id(self) -> str:
        return "hyperliquid"

    def __init__(
        self,
        wallet_address: str = "",
        private_key: str = "",
    ) -> None:
        self._ccxt = ccxt.hyperliquid(
            {
                "walletAddress": wallet_address,
                "privateKey": private_key,
                "enableRateLimit": True,
            }
        )

    @classmethod
    def from_settings(cls) -> HyperliquidExchange:
        """Construct from application settings."""
        return cls(
            wallet_address=settings.HYPERLIQUID_WALLET_ADDRESS,
            private_key=settings.HYPERLIQUID_PRIVATE_KEY,
        )

    # ── Overrides ───────────────────────────────────────────────────────────────

    async def fetch_funding_rates(self, symbols: list[str] | None = None) -> dict[str, Any]:
        """
        Hyperliquid has no bulk funding-rate endpoint.
        Falls back to sequential per-symbol fetches.
        """
        if not symbols:
            raise ExchangeError(
                "Hyperliquid requires an explicit symbols list for fetch_funding_rates",
                code="UNSUPPORTED_OPERATION",
            )
        results: dict[str, Any] = {}
        for sym in symbols:
            results[sym] = await self.fetch_funding_rate(sym)
        return results
