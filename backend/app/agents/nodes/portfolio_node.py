"""
Portfolio Agent node — loads portfolio balance, positions, open orders, and metrics.
Queries the database and CCXT client (when applicable) to populate state metrics.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
import uuid

from app.agents.graph.state import PortfolioMetrics, TradingState
from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.infrastructure.repositories.order_repository import OrderRepository
from app.infrastructure.repositories.portfolio_repository import (
    EquityRepository,
    PortfolioRepository,
)


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
        if state.portfolio_id and state.portfolio_metrics.total_value_usdt > 0:
            self._log_info("portfolio metrics already loaded, skipping for idempotency")
            return {
                "available_balance": state.available_balance,
                "open_positions": state.open_positions,
                "portfolio_metrics": state.portfolio_metrics,
            }

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
            metrics = await self.get_metrics(portfolio_id, balance, positions)

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
        balance: Decimal,
        positions: list[dict[str, Any]],
    ) -> PortfolioMetrics:
        if self._deps.session is None:
            return PortfolioMetrics()

        portfolio_repo = PortfolioRepository(self._deps.session)
        portfolio = await portfolio_repo.get_by_id(uuid.UUID(portfolio_id))
        if portfolio is None:
            return PortfolioMetrics()

        # 1. Retrieve open orders from repository
        order_repo = OrderRepository(self._deps.session)
        open_db_orders = await order_repo.get_open_orders(uuid.UUID(portfolio_id))
        open_orders = []
        for o in open_db_orders:
            open_orders.append(
                {
                    "id": str(o.id),
                    "symbol": o.symbol,
                    "side": str(o.side.value if hasattr(o.side, "value") else o.side),
                    "type": str(
                        o.order_type.value if hasattr(o.order_type, "value") else o.order_type
                    ),
                    "quantity": float(o.quantity),
                    "price": float(o.price) if o.price else None,
                    "status": str(o.status.value if hasattr(o.status, "value") else o.status),
                }
            )

        # 2. Calculate PnL, exposure, and margin metrics
        equity_repo = EquityRepository(self._deps.session)
        trade_pnls = await equity_repo.get_closed_trade_pnls(uuid.UUID(portfolio_id))

        total_trades = len(trade_pnls)
        winning_trades = sum(1 for pnl in trade_pnls if pnl > 0)
        win_rate = float(winning_trades / total_trades) if total_trades > 0 else 0.0

        total_val = portfolio.total_value_usdt
        daily_pnl = portfolio.daily_pnl
        daily_pnl_pct = float(daily_pnl / total_val) * 100 if total_val > 0 else 0.0

        # Exposure is the total dollar value of all open positions
        exposure = Decimal("0")
        for pos in positions:
            exposure += Decimal(str(pos["quantity"])) * Decimal(str(pos["current_price"]))

        total_pnl = portfolio.realized_pnl + portfolio.unrealized_pnl
        available_margin = balance  # In spot/paper trading, available margin is available balance

        # 3. Generate summary
        summary = self.generate_summary(
            balance=balance,
            total_val=total_val,
            exposure=exposure,
            daily_pnl=daily_pnl,
            total_pnl=total_pnl,
            positions=positions,
            open_orders=open_orders,
        )

        return PortfolioMetrics(
            total_value_usdt=total_val,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            unrealized_pnl=portfolio.unrealized_pnl,
            realized_pnl=portfolio.realized_pnl,
            total_pnl=total_pnl,
            exposure=exposure,
            available_margin=available_margin,
            open_orders=open_orders,
            summary=summary,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            sharpe_ratio=None,
        )

    def generate_summary(
        self,
        balance: Decimal,
        total_val: Decimal,
        exposure: Decimal,
        daily_pnl: Decimal,
        total_pnl: Decimal,
        positions: list[dict[str, Any]],
        open_orders: list[dict[str, Any]],
    ) -> str:
        pos_lines = []
        for pos in positions:
            pos_lines.append(
                f"- {pos['symbol']}: {pos['side']} {pos['quantity']} @ Entry {pos['entry_price']} | Current {pos['current_price']} | Unr PnL: {pos['unrealized_pnl']} ({pos['unrealized_pnl_pct'] * 100:.2f}%)"
            )
        pos_str = "\n".join(pos_lines) if pos_lines else "- No open positions."

        order_lines = []
        for o in open_orders:
            order_lines.append(
                f"- {o['symbol']}: {o['side']} {o['type']} {o['quantity']} @ {o['price'] or 'MKT'} (Status: {o['status']})"
            )
        order_str = "\n".join(order_lines) if order_lines else "- No open orders."

        return (
            f"=== Portfolio Summary ===\n"
            f"Current Balance: {balance} USDT\n"
            f"Total Equity: {total_val} USDT\n"
            f"Total Exposure: {exposure} USDT\n"
            f"Daily PnL: {daily_pnl} USDT\n"
            f"Total PnL: {total_pnl} USDT\n"
            f"\n--- Open Positions ---\n{pos_str}\n"
            f"\n--- Open Orders ---\n{order_str}"
        )
