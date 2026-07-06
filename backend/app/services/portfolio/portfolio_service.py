"""
PortfolioService — CRUD for user portfolios.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.domain.models.portfolio import Portfolio
from app.domain.schemas.common import PaginatedResponse
from app.domain.schemas.trading import PortfolioCreate, PortfolioResponse
from app.infrastructure.repositories.portfolio_repository import PortfolioRepository


class PortfolioService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PortfolioRepository(session)

    async def create_portfolio(
        self, user_id: uuid.UUID, payload: PortfolioCreate
    ) -> PortfolioResponse:
        portfolio = Portfolio(
            id=uuid.uuid4(),
            user_id=user_id,
            name=payload.name,
            exchange=payload.exchange,
            quote_currency=payload.quote_currency,
            is_paper_trading=payload.is_paper_trading,
        )
        portfolio = await self._repo.create(portfolio)
        return PortfolioResponse.model_validate(portfolio)

    async def get_portfolio(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> PortfolioResponse:
        portfolio = await self._repo.get_with_positions(portfolio_id)
        if portfolio is None:
            raise NotFoundError("Portfolio not found", code="PORTFOLIO_NOT_FOUND")
        if portfolio.user_id != user_id:
            raise AuthorizationError("Not your portfolio", code="FORBIDDEN")
        return PortfolioResponse.model_validate(portfolio)

    async def list_portfolios(
        self, user_id: uuid.UUID, offset: int = 0, limit: int = 20, page: int = 1
    ) -> PaginatedResponse[PortfolioResponse]:
        portfolios, total = await self._repo.get_by_user(user_id, offset=offset, limit=limit)
        items = [PortfolioResponse.model_validate(p) for p in portfolios]
        return PaginatedResponse.from_list(items, total=total, page=page, page_size=limit)

    async def delete_portfolio(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> None:
        portfolio = await self._repo.get_by_id(portfolio_id)
        if portfolio is None:
            raise NotFoundError("Portfolio not found", code="PORTFOLIO_NOT_FOUND")
        if portfolio.user_id != user_id:
            raise AuthorizationError("Not your portfolio", code="FORBIDDEN")
        await self._repo.delete(portfolio_id)
