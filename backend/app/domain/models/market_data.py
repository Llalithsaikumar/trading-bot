"""Market data ORM models (OHLCV + ticker snapshots)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, UUIDMixin


class OHLCV(UUIDMixin, Base):
    """OHLCV candlestick data — partitioned by symbol + timeframe in production."""

    __tablename__ = "ohlcv"
    __table_args__ = (
        UniqueConstraint("exchange", "symbol", "timeframe", "timestamp", name="uq_ohlcv"),
        Index("ix_ohlcv_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
    )

    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    open: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    quote_volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 8))
    trades_count: Mapped[int | None] = mapped_column(BigInteger)


class MarketTicker(UUIDMixin, Base):
    """Real-time ticker snapshot (latest price, 24h stats)."""

    __tablename__ = "market_tickers"
    __table_args__ = (UniqueConstraint("exchange", "symbol", name="uq_ticker"),)

    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    bid: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    ask: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    last: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    mark_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    index_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))

    volume_24h: Mapped[Decimal] = mapped_column(Numeric(30, 8))
    quote_volume_24h: Mapped[Decimal | None] = mapped_column(Numeric(30, 8))
    change_24h_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    high_24h: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    low_24h: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    funding_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 8))


class OrderBookSnapshot(UUIDMixin, Base):
    """Snapshot of bids and asks for a symbol at a given timestamp."""

    __tablename__ = "order_book_snapshots"

    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    bids: Mapped[list[list[float]]] = mapped_column(JSON, nullable=False)
    asks: Mapped[list[list[float]]] = mapped_column(JSON, nullable=False)


class TechnicalIndicator(UUIDMixin, Base):
    """Calculated technical indicators for a symbol and timeframe."""

    __tablename__ = "technical_indicators"
    __table_args__ = (
        UniqueConstraint(
            "exchange", "symbol", "timeframe", "timestamp", name="uq_technical_indicators"
        ),
    )

    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    rsi: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    ema_20: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    ema_50: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    macd: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    macd_signal: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    macd_histogram: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    atr: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    bb_upper: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    bb_middle: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    bb_lower: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    adx: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
