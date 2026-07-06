"""
Exchange factory — builds and caches typed ExchangeBase adapters.

Usage:
    exchange = get_exchange("binance")        # returns BinanceExchange
    exchange = get_exchange()                 # uses settings.EXCHANGE_DEFAULT
    await close_all_exchanges()              # call on app shutdown
"""
from __future__ import annotations

from app.core.config import settings
from app.core.exceptions import ExchangeError
from app.core.logging import logger

from .base import ExchangeBase
from .binance import BinanceExchange
from .bybit import BybitExchange
from .hyperliquid import HyperliquidExchange
from .okx import OKXExchange

_SUPPORTED: frozenset[str] = frozenset({"binance", "bybit", "okx", "hyperliquid"})
_pool: dict[str, ExchangeBase] = {}


def _build(exchange_id: str) -> ExchangeBase:
    match exchange_id:
        case "binance":
            return BinanceExchange.from_settings()
        case "bybit":
            return BybitExchange.from_settings()
        case "okx":
            return OKXExchange.from_settings()
        case "hyperliquid":
            return HyperliquidExchange.from_settings()
        case _:
            raise ExchangeError(
                f"Exchange '{exchange_id}' is not supported. "
                f"Supported: {sorted(_SUPPORTED)}",
                code="EXCHANGE_NOT_FOUND",
            )


def get_exchange(exchange_id: str | None = None) -> ExchangeBase:
    """
    Return a cached exchange adapter.
    Falls back to settings.EXCHANGE_DEFAULT when exchange_id is None.
    Thread-safe for asyncio (single event loop assumed).
    """
    name = (exchange_id or settings.EXCHANGE_DEFAULT).lower()
    if name not in _pool:
        _pool[name] = _build(name)
        logger.info("Exchange adapter created", exchange=name)
    return _pool[name]


async def close_all_exchanges() -> None:
    """Close every open exchange adapter. Call on application shutdown."""
    for name, adapter in list(_pool.items()):
        await adapter.close()
        logger.info("Exchange adapter closed", exchange=name)
    _pool.clear()
