"""Strategy request / response schemas."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pydantic import Field

from app.domain.enums.trading import StrategyStatus, TimeFrame
from app.domain.schemas.common import BaseSchema, TimestampSchema

import uuid


class StrategyCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    exchange: str
    symbols: list[str] = Field(min_length=1)
    timeframe: TimeFrame = TimeFrame.H1
    max_position_size_pct: Decimal = Field(default=Decimal("5.0"), gt=0, le=100)
    stop_loss_pct: Decimal = Field(default=Decimal("2.0"), gt=0)
    take_profit_pct: Decimal = Field(default=Decimal("4.0"), gt=0)
    max_open_positions: int = Field(default=3, ge=1, le=20)
    config: dict[str, Any] = Field(default_factory=dict)


class StrategyUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None
    symbols: list[str] | None = None
    timeframe: TimeFrame | None = None
    max_position_size_pct: Decimal | None = None
    stop_loss_pct: Decimal | None = None
    take_profit_pct: Decimal | None = None
    max_open_positions: int | None = None
    config: dict[str, Any] | None = None


class StrategyResponse(TimestampSchema):
    id: uuid.UUID
    name: str
    description: str | None
    exchange: str
    symbols: list[str]
    timeframe: TimeFrame
    status: StrategyStatus
    max_position_size_pct: Decimal
    stop_loss_pct: Decimal
    take_profit_pct: Decimal
    max_open_positions: int
    config: dict[str, Any]
    total_trades: int
    winning_trades: int
    total_pnl: Decimal
    sharpe_ratio: Decimal | None


class StrategyExecutionResponse(TimestampSchema):
    id: uuid.UUID
    strategy_id: uuid.UUID
    run_id: str
    status: str
    signal: str | None
    reasoning: str | None
    tokens_used: int
    duration_ms: int
    error_message: str | None
