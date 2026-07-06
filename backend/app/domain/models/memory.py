"""Long term memory ORM model."""

from __future__ import annotations

import uuid
from sqlalchemy import ForeignKey, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.domain.models.base import Base, TimestampMixin, UUIDMixin


class LongTermMemory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "long_term_memories"

    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[str] = mapped_column(String(100), nullable=False)

    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    signal: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    news_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    indicators_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    performance_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    reflection: Mapped[str | None] = mapped_column(Text, nullable=True)

    embedding_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    def __repr__(self) -> str:
        return f"<LongTermMemory strategy_id={self.strategy_id} run_id={self.run_id} signal={self.signal}>"
