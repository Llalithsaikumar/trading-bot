"""User ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums.user import UserRole, UserStatus
from app.domain.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.domain.models.portfolio import Portfolio
    from app.domain.models.strategy import Strategy


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))

    role: Mapped[UserRole] = mapped_column(String(20), default=UserRole.TRADER, nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        String(30), default=UserStatus.PENDING_VERIFICATION, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    two_fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    two_fa_secret: Mapped[str | None] = mapped_column(String(255))

    # Relationships (populated by service layer)
    portfolios: Mapped[list[Portfolio]] = relationship(back_populates="user", lazy="noload")
    strategies: Mapped[list[Strategy]] = relationship(back_populates="user", lazy="noload")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
