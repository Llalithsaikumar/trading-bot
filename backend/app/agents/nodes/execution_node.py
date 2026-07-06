"""
Execution Agent node — places orders on the exchange.

Only runs when state.risk_approved=True (conditional edge from RiskAgent).
No trading logic is implemented in this phase — stubs are in place for
the full order-placement implementation.
"""
from __future__ import annotations

from typing import Any

from app.agents.graph.state import TradingState
from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.agents.interfaces.execution_agent import IExecutionAgent
from app.domain.enums.trading import TradingSignal


class ExecutionAgent(BaseAgent):
    """
    Implements IExecutionAgent.

    Graph position: eighth (conditional — only reached when risk_approved=True).
    Populates: state.order_placed, state.order_id, state.execution_error
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)

    async def run(self, state: TradingState) -> dict[str, Any]:
        self._log_info(
            "executing order",
            signal=str(state.signal),
            confidence=state.confidence,
        )
        try:
            ok, reason = await self.can_execute(state)
            if not ok:
                self._log_warning("pre-flight check failed", reason=reason)
                return {
                    "order_placed": False,
                    "execution_error": f"Pre-flight failed: {reason}",
                }

            order_id, error = await self.execute(state)
            if error:
                self._log_error("execution failed", error=error)
                return {"order_placed": False, "execution_error": error}

            self._log_info("order placed", order_id=order_id)
            return {"order_placed": True, "order_id": order_id}
        except Exception as exc:
            return {
                **self._node_error(state, exc),
                "order_placed": False,
                "execution_error": str(exc),
            }

    # ── IExecutionAgent implementation ────────────────────────────────────────

    async def can_execute(
        self,
        state: TradingState,
    ) -> tuple[bool, str]:
        if state.signal is None:
            return False, "No signal available"
        if state.signal == TradingSignal.NEUTRAL:
            return False, "Signal is NEUTRAL — no order to place"
        if state.portfolio_id is None:
            return False, "No portfolio_id in state"
        if state.available_balance <= 0:
            return False, "Insufficient balance"
        return True, ""

    async def execute(
        self,
        state: TradingState,
    ) -> tuple[str | None, str | None]:
        if self._deps.session is None:
            return None, "Database session not available"

        import uuid

        from app.domain.schemas.trading import OrderCreate
        from app.infrastructure.repositories.portfolio_repository import PortfolioRepository
        from app.services.paper_trading.engine import PaperTradingEngine

        portfolio_repo = PortfolioRepository(self._deps.session)
        portfolio = await portfolio_repo.get_by_id(uuid.UUID(state.portfolio_id))
        if portfolio is None:
            return None, "Portfolio not found"

        if not portfolio.is_paper_trading:
            return None, "Live trading is not supported in this version"

        try:
            params = await self.signal_to_order_params(state.signal, state)
            payload = OrderCreate(**params)

            engine = PaperTradingEngine(self._deps.session)
            order = await engine.execute_order(portfolio, payload)

            order.strategy_id = uuid.UUID(state.strategy_id)
            order.agent_reasoning = state.reasoning
            self._deps.session.add(order)
            await self._deps.session.flush()
            return str(order.id), None
        except Exception as e:
            return None, str(e)

    async def signal_to_order_params(
        self,
        signal: TradingSignal,
        state: TradingState,
    ) -> dict[str, Any]:
        import uuid
        from decimal import Decimal

        from app.domain.enums.trading import OrderSide, OrderType, TimeInForce
        from app.domain.models.strategy import Strategy
        from app.infrastructure.repositories.portfolio_repository import PortfolioRepository

        primary_symbol = state.symbols[0] if state.symbols else ""
        ticker = state.tickers.get(primary_symbol, {})
        last_price = Decimal(str(ticker.get("last") or 0))
        if last_price <= 0:
            last_price = Decimal("1.0")

        strategy = await self._deps.session.get(Strategy, uuid.UUID(state.strategy_id))
        max_pos_pct = strategy.max_position_size_pct if strategy else Decimal("5.0")

        portfolio_repo = PortfolioRepository(self._deps.session)
        portfolio = await portfolio_repo.get_by_id(uuid.UUID(state.portfolio_id))

        total_val = portfolio.total_value_usdt if portfolio else Decimal("100000")
        position_size = total_val * (max_pos_pct / Decimal("100"))

        quantity = (position_size / last_price).quantize(Decimal("0.0001"))
        if quantity <= 0:
            quantity = Decimal("0.01")

        side = (
            OrderSide.BUY
            if signal in (TradingSignal.BUY, TradingSignal.STRONG_BUY)
            else OrderSide.SELL
        )
        order_type = OrderType.MARKET

        return {
            "portfolio_id": uuid.UUID(state.portfolio_id),
            "symbol": primary_symbol,
            "side": side,
            "order_type": order_type,
            "quantity": quantity,
            "price": None,
            "stop_price": state.suggested_stop_loss,
            "time_in_force": TimeInForce.GTC,
            "reduce_only": False,
        }
