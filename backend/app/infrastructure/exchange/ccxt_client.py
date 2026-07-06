"""
Backward-compatibility shim — delegates to factory.py.
Prefer importing from app.infrastructure.exchange directly.
"""
from __future__ import annotations

from .base import ExchangeBase
from .factory import close_all_exchanges, get_exchange

# Re-export the typed base as ExchangeClient for callers that used the old name.
ExchangeClient = ExchangeBase

__all__ = ["get_exchange", "close_all_exchanges", "ExchangeClient"]
