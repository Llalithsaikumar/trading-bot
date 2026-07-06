"""Price / event alerts."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, UUIDMixin


class Alert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)  # price_above, price_below, etc.
    condition_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_triggered: Mapped[bool] = mapped_column(default=False, nullable=False)
    notify_email: Mapped[bool] = mapped_column(default=True)
    notify_push: Mapped[bool] = mapped_column(default=False)
