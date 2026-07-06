"""
OrderService — place, cancel, and track orders.

Routes paper-trading orders through PaperTradingEngine.
Live trading path is reserved for future implementation.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.enums.trading import OrderStatus
from app.domain.schemas.trading import OrderCreate, OrderResponse
from app.infrastructure.repositories.order_repository import OrderRepository
from app.infrastructure.repositories.portfolio_repository import PortfolioRepository
from app.services.paper_trading.engine import PaperTradingEngine


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._order_repo = OrderRepository(session)
        self._portfolio_repo = PortfolioRepository(session)

    async def place_order(
        self,
        user_id: uuid.UUID,
        payload: OrderCreate,
    ) -> OrderResponse:
        """
        Place an order.  If the target portfolio is a paper portfolio,
        the order is simulated through PaperTradingEngine.
        Live portfolios raise NotImplementedError (future feature).
        """
        portfolio = await self._portfolio_repo.get_with_positions(payload.portfolio_id)
        if portfolio is None:
            raise NotFoundError(f"Portfolio {payload.portfolio_id} not found")
        if portfolio.user_id != user_id:
            raise NotFoundError("Portfolio not found")  # don't leak ownership info

        if portfolio.is_paper_trading:
            engine = PaperTradingEngine(self._session)
            order = await engine.execute_order(portfolio, payload)
            await self._session.commit()
            return OrderResponse.model_validate(order)

        raise NotImplementedError("Live trading is not enabled — use a paper portfolio")

    async def cancel_order(
        self,
        user_id: uuid.UUID,
        order_id: uuid.UUID,
    ) -> None:
        order = await self._order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found")

        portfolio = await self._portfolio_repo.get_by_id(order.portfolio_id)
        if portfolio is None or portfolio.user_id != user_id:
            raise NotFoundError("Order not found")

        if order.status not in (OrderStatus.OPEN, OrderStatus.PENDING):
            raise ValueError(f"Cannot cancel order with status {order.status}")

        order.status = OrderStatus.CANCELLED
        self._session.add(order)
        await self._session.commit()

    async def get_order(
        self,
        user_id: uuid.UUID,
        order_id: uuid.UUID,
    ) -> OrderResponse:
        order = await self._order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found")

        portfolio = await self._portfolio_repo.get_by_id(order.portfolio_id)
        if portfolio is None or portfolio.user_id != user_id:
            raise NotFoundError("Order not found")

        return OrderResponse.model_validate(order)

    async def list_orders(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[OrderResponse], int]:
        if portfolio_id:
            portfolio = await self._portfolio_repo.get_by_id(portfolio_id)
            if portfolio is None or portfolio.user_id != user_id:
                return [], 0
            orders, total = await self._order_repo.get_by_portfolio(
                portfolio_id, offset=offset, limit=limit
            )
        else:
            # Return orders across all user portfolios
            portfolios, _ = await self._portfolio_repo.get_by_user(user_id, limit=100)
            portfolio_ids = {p.id for p in portfolios}
            all_orders: list = []
            for pid in portfolio_ids:
                o, _ = await self._order_repo.get_by_portfolio(pid, offset=0, limit=limit)
                all_orders.extend(o)
            all_orders.sort(key=lambda o: o.created_at, reverse=True)
            total = len(all_orders)
            orders = all_orders[offset : offset + limit]

        return [OrderResponse.model_validate(o) for o in orders], total
