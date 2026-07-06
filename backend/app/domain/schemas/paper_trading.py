"""
Pydantic schemas for paper trading–specific API operations.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.domain.schemas.common import BaseSchema


class PaperPortfolioCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=100, examples=["My Paper Portfolio"])
    exchange: str = Field(default="binance", examples=["binance"])
    initial_balance: Decimal = Field(
        default=Decimal("10000"),
        gt=0,
        description="Starting USDT balance for the paper portfolio",
    )
    quote_currency: str = Field(default="USDT")


class PaperPortfolioReset(BaseSchema):
    initial_balance: Decimal = Field(
        default=Decimal("10000"),
        gt=0,
        description="Reset the portfolio to this USDT balance",
    )


class EquityPointResponse(BaseSchema):
    timestamp: datetime
    equity: Decimal
    balance: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    daily_pnl: Decimal


class RiskMetricsResponse(BaseSchema):
    # Trade stats
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    profit_factor: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    # Drawdown
    max_drawdown: Decimal
    max_drawdown_pct: Decimal
    # Return
    total_return: Decimal
    total_return_pct: Decimal
    # Risk-adjusted
    sharpe_ratio: Decimal | None = None
    sortino_ratio: Decimal | None = None
    calmar_ratio: Decimal | None = None
    # Other
    total_fees_paid: Decimal
    var_95: Decimal
    peak_equity: Decimal
    current_equity: Decimal
    initial_equity: Decimal
