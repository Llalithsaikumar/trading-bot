import uuid
from decimal import Decimal
import pytest

from app.agents.interfaces.base import AgentDependencies
from app.agents.nodes.portfolio_node import PortfolioAgent
from app.agents.graph.state import TradingState
from app.domain.enums.trading import OrderSide, OrderStatus, OrderType, PositionSide, TimeInForce
from app.domain.models.order import Order
from app.domain.models.portfolio import Portfolio, Position


@pytest.mark.anyio
async def test_portfolio_agent_run_and_metrics(db_session):
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # 1. Add portfolio to DB
    portfolio = Portfolio(
        id=portfolio_id,
        user_id=user_id,
        name="Test Portfolio",
        exchange="binance",
        is_paper_trading=True,
        quote_currency="USDT",
        available_balance=Decimal("10000.0"),
        total_value_usdt=Decimal("12000.0"),
        unrealized_pnl=Decimal("1500.0"),
        realized_pnl=Decimal("500.0"),
        daily_pnl=Decimal("200.0"),
    )
    db_session.add(portfolio)

    # 2. Add position to DB
    position = Position(
        portfolio_id=portfolio_id,
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.1"),
        entry_price=Decimal("45000.0"),
        current_price=Decimal("50000.0"),
        unrealized_pnl=Decimal("500.0"),
        unrealized_pnl_pct=Decimal("0.1111"),
    )
    db_session.add(position)

    # 3. Add open order to DB
    order = Order(
        portfolio_id=portfolio_id,
        symbol="BTC/USDT",
        exchange="binance",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        status=OrderStatus.OPEN,
        time_in_force=TimeInForce.GTC,
        quantity=Decimal("0.05"),
        price=Decimal("48000.0"),
        filled_quantity=Decimal("0.0"),
    )
    db_session.add(order)
    await db_session.commit()

    # 4. Initialize agent
    deps = AgentDependencies(session=db_session)
    agent = PortfolioAgent(deps)

    # 5. Run agent
    state = TradingState(
        strategy_id="test-strategy", exchange="binance", symbols=["BTC/USDT"], timeframe="1h"
    )
    state.portfolio_id = str(portfolio_id)

    res = await agent.run(state)
    assert "available_balance" in res
    assert res["available_balance"] == Decimal("10000.0")
    assert len(res["open_positions"]) == 1

    metrics = res["portfolio_metrics"]
    assert metrics.total_value_usdt == Decimal("12000.0")
    assert metrics.daily_pnl == Decimal("200.0")
    assert metrics.total_pnl == Decimal("2000.0")  # realized (500) + unrealized (1500)
    assert metrics.exposure == Decimal("5000.0")  # 0.1 * 50000.0
    assert metrics.available_margin == Decimal("10000.0")
    assert len(metrics.open_orders) == 1
    assert metrics.open_orders[0]["symbol"] == "BTC/USDT"
    assert "=== Portfolio Summary ===" in metrics.summary
