"""
Portfolio Agent node — loads portfolio balance, positions, and metrics.

Queries the database for the active portfolio associated with the strategy,
and optionally reconciles with the live exchange balance.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.agents.graph.state import PortfolioMetrics, TradingState
from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.agents.interfaces.portfolio_agent import IPortfolioAgent


class PortfolioAgent(BaseAgent):
    """
    Implements IPortfolioAgent.

    Graph position: fifth (after TechnicalAgent).
    Populates: state.portfolio_id, state.available_balance,
               state.open_positions, state.portfolio_metrics
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)

    async def run(self, state: TradingState) -> dict[str, Any]:
        portfolio_id = state.portfolio_id
        self._log_info("loading portfolio", portfolio_id=portfolio_id)
        try:
            if portfolio_id is None:
                self._log_warning("no portfolio_id in state; using defaults")
                return {
                    "available_balance": Decimal("0"),
                    "open_positions": [],
                    "portfolio_metrics": PortfolioMetrics(),
                }

            balance, positions = await self.load_portfolio(portfolio_id)
            metrics = await self.get_metrics(portfolio_id)

            self._log_info(
                "portfolio loaded",
                balance=str(balance),
                open_positions=len(positions),
            )
            return {
                "available_balance": balance,
                "open_positions": positions,
                "portfolio_metrics": metrics,
            }
        except Exception as exc:
            return self._node_error(state, exc)

    # ── IPortfolioAgent implementation ────────────────────────────────────────

    async def load_portfolio(
        self,
        portfolio_id: str,
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        if self._deps.session is None:
            return Decimal("0"), []

        import uuid

        from app.infrastructure.repositories.portfolio_repository import PortfolioRepository

        repo = PortfolioRepository(self._deps.session)
        portfolio = await repo.get_with_positions(uuid.UUID(portfolio_id))

        if portfolio is None:
            return Decimal("0"), []

        positions = []
        for pos in portfolio.positions:
            positions.append(
                {
                    "symbol": pos.symbol,
                    "side": str(pos.side),
                    "quantity": float(pos.quantity),
                    "entry_price": float(pos.entry_price),
                    "current_price": float(pos.current_price),
                    "unrealized_pnl": float(pos.unrealized_pnl),
                    "unrealized_pnl_pct": float(pos.unrealized_pnl_pct),
                }
            )

        return portfolio.available_balance, positions

    async def get_metrics(
        self,
        portfolio_id: str,
    ) -> PortfolioMetrics:
        from app.agents.graph.state import PortfolioMetrics

        if self._deps.session is None:
            return PortfolioMetrics()

        import uuid

        from app.infrastructure.repositories.portfolio_repository import (
            EquityRepository,
            PortfolioRepository,
        )

        portfolio_repo = PortfolioRepository(self._deps.session)
        portfolio = await portfolio_repo.get_by_id(uuid.UUID(portfolio_id))
        if portfolio is None:
            return PortfolioMetrics()

        equity_repo = EquityRepository(self._deps.session)
        trade_pnls = await equity_repo.get_closed_trade_pnls(uuid.UUID(portfolio_id))

        total_trades = len(trade_pnls)
        winning_trades = sum(1 for pnl in trade_pnls if pnl > 0)
        win_rate = float(winning_trades / total_trades) if total_trades > 0 else 0.0

        total_val = portfolio.total_value_usdt
        daily_pnl = portfolio.daily_pnl
        daily_pnl_pct = float(daily_pnl / total_val) * 100 if total_val > 0 else 0.0

        return PortfolioMetrics(
            total_value_usdt=total_val,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            unrealized_pnl=portfolio.unrealized_pnl,
            realized_pnl=portfolio.realized_pnl,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            sharpe_ratio=None,
        )

