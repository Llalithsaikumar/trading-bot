"""IPortfolioAgent — contract for loading portfolio state and metrics."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from app.agents.graph.state import PortfolioMetrics


@runtime_checkable
class IPortfolioAgent(Protocol):
    """
    Structural interface for the Portfolio Agent node.

    Implementations load the current portfolio balance, open positions,
    and performance metrics from the database (or exchange directly for
    live paper-trading reconciliation).
    """

    async def load_portfolio(
        self,
        portfolio_id: str,
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """
        Fetch available balance and open positions for a portfolio.

        Args:
            portfolio_id: UUID string of the portfolio to load.

        Returns:
            Tuple of (available_balance_usdt, list_of_open_position_dicts).
            Each position dict: {symbol, side, quantity, entry_price,
                                 current_price, unrealized_pnl, leverage}
        """
        ...

    async def get_metrics(
        self,
        portfolio_id: str,
    ) -> PortfolioMetrics:
        """
        Compute or retrieve cached portfolio performance metrics.

        Args:
            portfolio_id: UUID string of the portfolio.

        Returns:
            PortfolioMetrics with win_rate, daily_pnl, sharpe_ratio etc.
        """
        ...
