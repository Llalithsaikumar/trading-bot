"""Polymarket domain schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.domain.schemas.common import BaseSchema


class PolymarketMarketResponse(BaseSchema):
    condition_id: str
    question: str
    description: str | None = None
    outcome_yes_price: Decimal
    outcome_no_price: Decimal
    probability: float  # YES price as float (0.0 to 1.0)
    liquidity: Decimal
    volume: Decimal
    volume_24h: Decimal
    end_date: datetime | None = None
    category: str | None = None
    active: bool
    fetched_at: datetime


class PolymarketSummaryResponse(BaseSchema):
    total_markets: int
    avg_probability: float
    total_liquidity: Decimal
    markets: list[PolymarketMarketResponse]
