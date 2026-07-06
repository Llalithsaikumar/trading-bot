"""Order ORM model."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums.trading import OrderSide, OrderStatus, OrderType, TimeInForce
from app.domain.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.domain.models.portfolio import Portfolio


class Order(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    exchange_order_id: Mapped[str | None] = mapped_column(String(100), index=True)

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[OrderSide] = mapped_column(String(10), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(String(30), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        String(30), default=OrderStatus.PENDING, nullable=False, index=True
    )
    time_in_force: Mapped[TimeInForce] = mapped_column(
        String(10), default=TimeInForce.GTC, nullable=False
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))        # None for market orders
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    average_fill_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    fee: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    fee_currency: Mapped[str | None] = mapped_column(String(10))

    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    reduce_only: Mapped[bool] = mapped_column(default=False)

    # AI metadata
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    agent_reasoning: Mapped[str | None] = mapped_column(String(2000))  # LLM reasoning snapshot

    # Relationships
    portfolio: Mapped[Portfolio | None] = relationship(lazy="noload")

    def __repr__(self) -> str:
        return f"<Order {self.side} {self.symbol} qty={self.quantity} status={self.status}>"
