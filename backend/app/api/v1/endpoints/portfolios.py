"""Portfolio CRUD endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status

from app.core.dependencies import Pagination, get_current_active_user, get_db
from app.domain.schemas.common import PaginatedResponse
from app.domain.schemas.trading import PortfolioCreate, PortfolioResponse
from app.services.portfolio.portfolio_service import PortfolioService

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


def _portfolio_service(session: AsyncSession = Depends(get_db)) -> PortfolioService:
    return PortfolioService(session=session)


@router.get("", response_model=PaginatedResponse[PortfolioResponse])
async def list_portfolios(
    pagination: Pagination,
    current_user=Depends(get_current_active_user),
    svc: PortfolioService = Depends(_portfolio_service),
) -> PaginatedResponse[PortfolioResponse]:
    return await svc.list_portfolios(
        user_id=current_user.id,
        offset=pagination.offset,
        limit=pagination.page_size,
        page=pagination.page,
    )


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    payload: PortfolioCreate,
    current_user=Depends(get_current_active_user),
    svc: PortfolioService = Depends(_portfolio_service),
) -> PortfolioResponse:
    return await svc.create_portfolio(user_id=current_user.id, payload=payload)


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
    svc: PortfolioService = Depends(_portfolio_service),
) -> PortfolioResponse:
    return await svc.get_portfolio(portfolio_id=portfolio_id, user_id=current_user.id)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
    svc: PortfolioService = Depends(_portfolio_service),
) -> None:
    await svc.delete_portfolio(portfolio_id=portfolio_id, user_id=current_user.id)
