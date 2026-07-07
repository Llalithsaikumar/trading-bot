"""Polymarket market snapshot ORM model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, UUIDMixin


class PolymarketSnapshot(UUIDMixin, TimestampMixin, Base):
    """Snapshot of a Polymarket market's status/prices at a given time."""

    __tablename__ = "polymarket_snapshots"
    __table_args__ = (
        Index("ix_polymarket_snapshots_condition_fetched", "condition_id", "fetched_at"),
    )

    condition_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    outcome_yes_price: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    outcome_no_price: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    liquidity: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    volume_24h: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
