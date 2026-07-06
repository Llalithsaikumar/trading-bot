"""Portfolio, Position, and EquityPoint repository queries."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domain.models.portfolio import EquityPoint, Portfolio, Position
from app.infrastructure.repositories.base import BaseRepository


class PortfolioRepository(BaseRepository[Portfolio]):
    model = Portfolio

    async def get_by_user(
        self, user_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[Portfolio], int]:
        return await self.get_all(offset=offset, limit=limit, user_id=user_id)

    async def get_with_positions(self, portfolio_id: uuid.UUID) -> Portfolio | None:
        stmt = (
            select(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .options(selectinload(Portfolio.positions))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_paper_portfolios(self, user_id: uuid.UUID) -> list[Portfolio]:
        stmt = select(Portfolio).where(
            Portfolio.user_id == user_id,
            Portfolio.is_paper_trading.is_(True),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class EquityRepository(BaseRepository[EquityPoint]):
    model = EquityPoint

    async def get_history(
        self,
        portfolio_id: uuid.UUID,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[EquityPoint]:
        stmt = (
            select(EquityPoint)
            .where(EquityPoint.portfolio_id == portfolio_id)
            .order_by(EquityPoint.timestamp.asc())
        )
        if since:
            stmt = stmt.where(EquityPoint.timestamp >= since)
        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_equity_values(self, portfolio_id: uuid.UUID) -> list[Decimal]:
        """Return ordered equity values for risk metric computation."""
        stmt = (
            select(EquityPoint.equity)
            .where(EquityPoint.portfolio_id == portfolio_id)
            .order_by(EquityPoint.timestamp.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_closed_trade_pnls(self, portfolio_id: uuid.UUID) -> list[Decimal]:
        """
        Return realized_pnl deltas between consecutive snapshots.
        Non-zero deltas indicate a trade was closed at that point.
        """
        rows = await self.get_equity_values(portfolio_id)
        if not rows:
            return []
        # Compute incremental realized PnL changes
        stmt = (
            select(EquityPoint.realized_pnl)
            .where(EquityPoint.portfolio_id == portfolio_id)
            .order_by(EquityPoint.timestamp.asc())
        )
        result = await self._session.execute(stmt)
        rpnls = list(result.scalars().all())

        deltas: list[Decimal] = []
        for i in range(1, len(rpnls)):
            delta = rpnls[i] - rpnls[i - 1]
            if abs(delta) > Decimal("0.000001"):
                deltas.append(delta)
        return deltas
