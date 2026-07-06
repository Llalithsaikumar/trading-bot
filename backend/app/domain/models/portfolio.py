"""Portfolio, Position, and EquityPoint ORM models."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums.trading import PositionSide
from app.domain.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.domain.models.user import User


class Portfolio(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "portfolios"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(10), default="USDT", nullable=False)

    # Balances
    initial_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("0"), nullable=False,
        comment="Starting balance set at creation; used to compute total return",
    )
    total_value_usdt: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    available_balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    daily_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))

    is_paper_trading: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    user: Mapped[User] = relationship(back_populates="portfolios")
    positions: Mapped[list[Position]] = relationship(
        back_populates="portfolio", lazy="noload", cascade="all, delete-orphan"
    )
    equity_history: Mapped[list[EquityPoint]] = relationship(
        back_populates="portfolio", lazy="noload", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Portfolio id={self.id} name={self.name!r} paper={self.is_paper_trading}>"


class Position(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "positions"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[PositionSide] = mapped_column(String(10), nullable=False)

    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    liquidation_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))

    leverage: Mapped[int] = mapped_column(default=1, nullable=False)
    margin_used: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    unrealized_pnl_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))

    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))

    portfolio: Mapped[Portfolio] = relationship(back_populates="positions")

    def __repr__(self) -> str:
        return f"<Position {self.symbol} {self.side} qty={self.quantity}>"


class EquityPoint(UUIDMixin, Base):
    """
    Time-series snapshot of portfolio equity.
    Written after every fill and on periodic price syncs.
    Used for PnL charting and risk metric computation.
    """

    __tablename__ = "equity_history"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    equity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    daily_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))

    portfolio: Mapped[Portfolio] = relationship(back_populates="equity_history")

    def __repr__(self) -> str:
        return f"<EquityPoint pid={self.portfolio_id} ts={self.timestamp} eq={self.equity}>"
