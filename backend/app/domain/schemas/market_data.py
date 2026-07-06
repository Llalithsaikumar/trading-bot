"""Market data schemas."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.domain.schemas.common import BaseSchema


class OHLCVResponse(BaseSchema):
    timestamp: str  # unix ms as string for interop
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class TickerResponse(BaseSchema):
    exchange: str
    symbol: str
    timestamp: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume_24h: Decimal
    change_24h_pct: Decimal | None = None
    high_24h: Decimal | None = None
    low_24h: Decimal | None = None
    funding_rate: Decimal | None = None


class OrderBookResponse(BaseSchema):
    exchange: str
    symbol: str
    # bids/asks: list of [price, size] pairs
    bids: list[list[Decimal]]
    asks: list[list[Decimal]]
    timestamp: str = ""


class MarketSummaryResponse(BaseSchema):
    exchange: str
    symbol: str
    last: Decimal
    change_24h_pct: Decimal | None = None
    volume_24h: Decimal
    high_24h: Decimal | None = None
    low_24h: Decimal | None = None
