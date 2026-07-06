"""Trading schemas: orders, positions, portfolios."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field, model_validator

from app.domain.enums.trading import OrderSide, OrderStatus, OrderType, PositionSide, TimeInForce
from app.domain.schemas.common import BaseSchema, TimestampSchema

if TYPE_CHECKING:
    import uuid
    from decimal import Decimal


# ─── Order ─────────────────────────────────────────────────────────────────────
class OrderCreate(BaseSchema):
    portfolio_id: uuid.UUID
    symbol: str = Field(examples=["BTC/USDT"])
    side: OrderSide
    order_type: OrderType
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    stop_price: Decimal | None = Field(default=None, gt=0)
    time_in_force: TimeInForce = TimeInForce.GTC
    reduce_only: bool = False

    @model_validator(mode="after")
    def validate_price_for_limit_orders(self) -> OrderCreate:
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("price is required for LIMIT orders")
        return self


class OrderResponse(TimestampSchema):
    id: uuid.UUID
    exchange_order_id: str | None
    symbol: str
    exchange: str
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    time_in_force: TimeInForce
    quantity: Decimal
    price: Decimal | None
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    fee: Decimal
    fee_currency: str | None
    agent_reasoning: str | None


# ─── Position ──────────────────────────────────────────────────────────────────
class PositionResponse(TimestampSchema):
    id: uuid.UUID
    symbol: str
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    leverage: int
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    stop_loss: Decimal | None
    take_profit: Decimal | None


# ─── Portfolio ─────────────────────────────────────────────────────────────────
class PortfolioCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=100)
    exchange: str
    quote_currency: str = "USDT"
    is_paper_trading: bool = False


class PortfolioResponse(TimestampSchema):
    id: uuid.UUID
    name: str
    exchange: str
    quote_currency: str
    total_value_usdt: Decimal
    available_balance: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    daily_pnl: Decimal
    is_paper_trading: bool
    positions: list[PositionResponse] = []
