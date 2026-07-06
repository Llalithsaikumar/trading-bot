"""Strategy and StrategyExecution ORM models."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums.trading import StrategyStatus, TimeFrame
from app.domain.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.domain.models.user import User


class Strategy(UUIDMixin, TimestampMixin, Base):
    """
    Represents a trading strategy configuration.
    The actual logic is executed by LangGraph agents.
    """
    __tablename__ = "strategies"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    symbols: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    timeframe: Mapped[TimeFrame] = mapped_column(String(10), default=TimeFrame.H1, nullable=False)

    status: Mapped[StrategyStatus] = mapped_column(
        String(20), default=StrategyStatus.PAUSED, nullable=False, index=True
    )

    # Risk parameters
    max_position_size_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("5.0"))
    stop_loss_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("2.0"))
    take_profit_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("4.0"))
    max_open_positions: Mapped[int] = mapped_column(default=3)

    # Strategy configuration (arbitrary JSON for agent prompts, indicators, etc.)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Performance metrics (denormalised for fast reads)
    total_trades: Mapped[int] = mapped_column(default=0)
    winning_trades: Mapped[int] = mapped_column(default=0)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    user: Mapped[User] = relationship(back_populates="strategies")
    executions: Mapped[list[StrategyExecution]] = relationship(
        back_populates="strategy", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Strategy '{self.name}' status={self.status}>"


class StrategyExecution(UUIDMixin, TimestampMixin, Base):
    """Records each LangGraph agent run for a strategy."""
    __tablename__ = "strategy_executions"

    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[str] = mapped_column(String(100), index=True)  # LangGraph run ID
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    signal: Mapped[str | None] = mapped_column(String(20))
    reasoning: Mapped[str | None] = mapped_column(Text)
    tokens_used: Mapped[int] = mapped_column(default=0)
    duration_ms: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(Text)

    strategy: Mapped[Strategy] = relationship(back_populates="executions")
