"""
Execution Agent node — places orders on the exchange.
Only runs when state.risk_approved=True (conditional edge from RiskAgent).
Connects to BaseExchange (both PaperExchange and live exchanges like BinanceExchange).
Handles order validation, placement, transaction rollbacks, and unified logging.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any
import uuid

from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.domain.enums.trading import TradingSignal
from app.domain.models.order import Order

if TYPE_CHECKING:
    from app.agents.graph.state import TradingState
    from app.infrastructure.exchange.base import BaseExchange


class ExecutionAgent(BaseAgent):
    """
    Implements IExecutionAgent.
    Graph position: eighth (conditional — only reached when risk_approved=True).
    Populates: state.order_placed, state.order_id, state.execution_error
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)

    async def run(self, state: TradingState) -> dict[str, Any]:
        if state.order_placed or state.order_id:
            self._log_info("order already placed, skipping for idempotency", order_id=state.order_id)
            return {"order_placed": True, "order_id": state.order_id}

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

            self._log_info("order placed successfully", order_id=order_id)
            return {"order_placed": True, "order_id": order_id}
        except Exception as exc:
            self._log_error("unexpected execution error, rolling back", error=str(exc))
            if self._deps.session:
                await self._deps.session.rollback()
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

        from app.infrastructure.repositories.portfolio_repository import PortfolioRepository

        portfolio_repo = PortfolioRepository(self._deps.session)
        portfolio = await portfolio_repo.get_by_id(uuid.UUID(state.portfolio_id))
        if portfolio is None:
            return None, f"Portfolio {state.portfolio_id} not found"

        try:
            # 1. Connect to BaseExchange via dynamic adapter selection
            exchange = self.get_exchange_adapter(portfolio)

            # 2. Convert signal to CCXT-compatible order parameters
            params = await self.signal_to_order_params(state.signal, state)

            symbol = params["symbol"]
            side = str(params["side"].value if hasattr(params["side"], "value") else params["side"])
            order_type = str(
                params["order_type"].value
                if hasattr(params["order_type"], "value")
                else params["order_type"]
            )
            quantity = float(params["quantity"])
            price = float(params["price"]) if params["price"] else None

            self._log_info(
                "sending order request to exchange",
                exchange_id=exchange.exchange_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
            )

            # 3. Place order via abstract BaseExchange interface
            if order_type.lower() == "market":
                order_res = await exchange.create_market_order(
                    symbol=symbol,
                    side=side,
                    amount=quantity,
                    params={"stopPrice": float(state.suggested_stop_loss)}
                    if state.suggested_stop_loss
                    else None,
                )
            else:
                order_res = await exchange.create_limit_order(
                    symbol=symbol,
                    side=side,
                    amount=quantity,
                    price=price,
                    params={"stopPrice": float(state.suggested_stop_loss)}
                    if state.suggested_stop_loss
                    else None,
                )

            self._log_info("exchange order executed", response=order_res)

            # 4. Persistence management and Unified Logging
            if portfolio.is_paper_trading:
                # The PaperExchange adapter already created, processed and flushed the Order model inside PaperTradingEngine.
                # We fetch it by UUID and record the strategy relation and agent reasoning.
                order_id = order_res["id"]
                db_order = await self._deps.session.get(Order, uuid.UUID(order_id))
                if db_order:
                    db_order.strategy_id = uuid.UUID(state.strategy_id)
                    db_order.agent_reasoning = state.reasoning
                    self._deps.session.add(db_order)
                    await self._deps.session.flush()
            else:
                # For real exchanges (e.g. BinanceExchange), build and persist a new Order log record
                from app.domain.enums.trading import (
                    OrderSide as EnumOrderSide,
                    OrderStatus as EnumOrderStatus,
                    OrderType as EnumOrderType,
                )

                db_order = Order(
                    portfolio_id=portfolio.id,
                    strategy_id=uuid.UUID(state.strategy_id),
                    symbol=symbol,
                    exchange=portfolio.exchange,
                    side=EnumOrderSide(side.lower()),
                    order_type=EnumOrderType(order_type.lower()),
                    status=EnumOrderStatus(order_res.get("status", "open").lower()),
                    quantity=Decimal(str(quantity)),
                    price=Decimal(str(price)) if price else None,
                    filled_quantity=Decimal(str(order_res.get("filled", 0.0))),
                    exchange_order_id=str(order_res.get("id")),
                    agent_reasoning=state.reasoning,
                )
                self._deps.session.add(db_order)
                await self._deps.session.flush()
                order_id = str(db_order.id)

            return order_id, None

        except Exception as e:
            self._log_error("order placement failed, executing rollback", error=str(e))
            # Rollback database transaction on failure
            await self._deps.session.rollback()
            return None, str(e)

    def get_exchange_adapter(self, portfolio: Any) -> BaseExchange:
        """Returns the appropriate BaseExchange implementation for paper or live trades."""
        if self._deps.exchange:
            return self._deps.exchange

        if portfolio.is_paper_trading:
            from app.infrastructure.exchange.paper import PaperExchange

            return PaperExchange(
                portfolio_id=portfolio.id,
                session=self._deps.session,
                exchange_id=portfolio.exchange,
            )
        else:
            from app.infrastructure.exchange.factory import get_exchange

            return get_exchange(portfolio.exchange)

    async def signal_to_order_params(
        self,
        signal: TradingSignal,
        state: TradingState,
    ) -> dict[str, Any]:
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

        if state.suggested_size and state.suggested_size > Decimal("0"):
            quantity = state.suggested_size.quantize(Decimal("0.0001"))
        else:
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
