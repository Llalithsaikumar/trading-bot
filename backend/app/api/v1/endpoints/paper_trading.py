"""
Paper trading–specific endpoints.

These supplement the generic /portfolios and /orders routes with
operations that only make sense in paper trading context:
  - Create a paper portfolio with an explicit starting balance
  - Get equity history (for PnL charts)
  - Get risk metrics (Sharpe, drawdown, win rate, …)
  - Reset a portfolio back to its initial balance
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_current_active_user, get_db
from app.core.exceptions import NotFoundError
from app.domain.models.portfolio import EquityPoint, Portfolio
from app.domain.schemas.paper_trading import (
    EquityPointResponse,
    PaperPortfolioCreate,
    PaperPortfolioReset,
    RiskMetricsResponse,
)
from app.domain.schemas.trading import PortfolioResponse
from app.infrastructure.repositories.order_repository import OrderRepository
from app.infrastructure.repositories.portfolio_repository import (
    EquityRepository,
    PortfolioRepository,
)
from app.services.paper_trading import risk_metrics as rm

router = APIRouter()


@router.post(
    "/portfolios",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a paper trading portfolio",
)
async def create_paper_portfolio(
    payload: PaperPortfolioCreate,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db),
):
    """
    Create a new paper portfolio seeded with `initial_balance` USDT.
    No live funds are involved.
    """
    portfolio = Portfolio(
        user_id=current_user.id,
        name=payload.name,
        exchange=payload.exchange,
        quote_currency=payload.quote_currency,
        initial_balance=payload.initial_balance,
        available_balance=payload.initial_balance,
        total_value_usdt=payload.initial_balance,
        is_paper_trading=True,
    )
    repo = PortfolioRepository(db)
    portfolio = await repo.create(portfolio)

    # Record the opening equity snapshot
    equity_repo = EquityRepository(db)
    opening = EquityPoint(
        portfolio_id=portfolio.id,
        timestamp=datetime.now(UTC),
        equity=payload.initial_balance,
        balance=payload.initial_balance,
        unrealized_pnl=Decimal("0"),
        realized_pnl=Decimal("0"),
        daily_pnl=Decimal("0"),
    )
    await equity_repo.create(opening)
    await db.commit()
    await db.refresh(portfolio)
    return PortfolioResponse.model_validate(portfolio)


@router.post(
    "/portfolios/{portfolio_id}/reset",
    response_model=PortfolioResponse,
    summary="Reset a paper portfolio to its initial balance",
)
async def reset_paper_portfolio(
    portfolio_id: uuid.UUID,
    payload: PaperPortfolioReset,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db),
):
    """
    Wipe all positions, orders, and equity history for this paper portfolio
    and restore the balance to `initial_balance`.
    """
    repo = PortfolioRepository(db)
    portfolio = await repo.get_with_positions(portfolio_id)
    if portfolio is None or portfolio.user_id != current_user.id:
        raise NotFoundError("Portfolio not found")
    if not portfolio.is_paper_trading:
        raise ValueError("Cannot reset a live portfolio")

    # Delete positions (cascade will remove child equity rows too)
    from sqlalchemy import delete as sa_delete
    from app.domain.models.portfolio import Position

    await db.execute(sa_delete(Position).where(Position.portfolio_id == portfolio_id))
    await db.execute(sa_delete(EquityPoint).where(EquityPoint.portfolio_id == portfolio_id))

    portfolio.initial_balance = payload.initial_balance
    portfolio.available_balance = payload.initial_balance
    portfolio.total_value_usdt = payload.initial_balance
    portfolio.unrealized_pnl = Decimal("0")
    portfolio.realized_pnl = Decimal("0")
    portfolio.daily_pnl = Decimal("0")
    db.add(portfolio)

    equity_repo = EquityRepository(db)
    await equity_repo.create(
        EquityPoint(
            portfolio_id=portfolio.id,
            timestamp=datetime.now(UTC),
            equity=payload.initial_balance,
            balance=payload.initial_balance,
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            daily_pnl=Decimal("0"),
        )
    )
    await db.commit()
    await db.refresh(portfolio)
    return PortfolioResponse.model_validate(portfolio)


@router.get(
    "/portfolios/{portfolio_id}/equity",
    response_model=list[EquityPointResponse],
    summary="Equity curve for PnL charting",
)
async def get_equity_history(
    portfolio_id: uuid.UUID,
    since: datetime | None = Query(default=None, description="ISO-8601 start datetime"),
    limit: int = Query(default=500, ge=1, le=2000),
    current_user=Depends(get_current_active_user),
    db=Depends(get_db),
):
    repo = PortfolioRepository(db)
    portfolio = await repo.get_by_id(portfolio_id)
    if portfolio is None or portfolio.user_id != current_user.id:
        raise NotFoundError("Portfolio not found")

    eq_repo = EquityRepository(db)
    points = await eq_repo.get_history(portfolio_id, since=since, limit=limit)
    return [EquityPointResponse.model_validate(p) for p in points]


@router.get(
    "/portfolios/{portfolio_id}/risk-metrics",
    response_model=RiskMetricsResponse,
    summary="Risk metrics: Sharpe, drawdown, win rate, VaR …",
)
async def get_risk_metrics(
    portfolio_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db),
):
    repo = PortfolioRepository(db)
    portfolio = await repo.get_by_id(portfolio_id)
    if portfolio is None or portfolio.user_id != current_user.id:
        raise NotFoundError("Portfolio not found")

    eq_repo = EquityRepository(db)
    equity_values = await eq_repo.get_equity_values(portfolio_id)
    trade_pnls = await eq_repo.get_closed_trade_pnls(portfolio_id)
    total_fees = sum(o.fee for o in await OrderRepository(db).get_filled_by_portfolio(portfolio_id))

    metrics = rm.compute(
        equity_history=equity_values,
        initial_equity=portfolio.initial_balance or Decimal("10000"),
        current_equity=portfolio.total_value_usdt,
        trade_pnls=trade_pnls,
        total_fees=total_fees,
    )

    return RiskMetricsResponse(
        total_trades=metrics.total_trades,
        winning_trades=metrics.winning_trades,
        losing_trades=metrics.losing_trades,
        win_rate=metrics.win_rate,
        profit_factor=metrics.profit_factor,
        avg_win=metrics.avg_win,
        avg_loss=metrics.avg_loss,
        max_drawdown=metrics.max_drawdown,
        max_drawdown_pct=metrics.max_drawdown_pct,
        total_return=metrics.total_return,
        total_return_pct=metrics.total_return_pct,
        sharpe_ratio=metrics.sharpe_ratio,
        sortino_ratio=metrics.sortino_ratio,
        calmar_ratio=metrics.calmar_ratio,
        total_fees_paid=metrics.total_fees_paid,
        var_95=metrics.var_95,
        peak_equity=metrics.peak_equity,
        current_equity=metrics.current_equity,
        initial_equity=portfolio.initial_balance or Decimal("0"),
    )
