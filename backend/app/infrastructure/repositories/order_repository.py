"""Order-specific repository queries."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.domain.enums.trading import OrderStatus
from app.domain.models.order import Order
from app.infrastructure.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    model = Order

    async def get_by_portfolio(
        self,
        portfolio_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        status: OrderStatus | None = None,
        symbol: str | None = None,
    ) -> tuple[list[Order], int]:
        filters: dict = {"portfolio_id": portfolio_id}
        if status:
            filters["status"] = status
        if symbol:
            filters["symbol"] = symbol
        return await self.get_all(offset=offset, limit=limit, **filters)

    async def get_open_orders(self, portfolio_id: uuid.UUID) -> list[Order]:
        stmt = select(Order).where(
            Order.portfolio_id == portfolio_id,
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_exchange_id(
        self, exchange_order_id: str, exchange: str
    ) -> Order | None:
        stmt = select(Order).where(
            Order.exchange_order_id == exchange_order_id,
            Order.exchange == exchange,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_filled_by_portfolio(self, portfolio_id: uuid.UUID) -> list[Order]:
        stmt = (
            select(Order)
            .where(
                Order.portfolio_id == portfolio_id,
                Order.status == OrderStatus.FILLED,
            )
            .order_by(Order.updated_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_filled(self, portfolio_id: uuid.UUID) -> int:
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(Order)
            .where(
                Order.portfolio_id == portfolio_id,
                Order.status == OrderStatus.FILLED,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
