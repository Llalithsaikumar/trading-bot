import uuid
from decimal import Decimal
from unittest.mock import AsyncMock
import pytest

from app.agents.graph.state import TradingState
from app.agents.interfaces.base import AgentDependencies
from app.agents.nodes.execution_node import ExecutionAgent
from app.domain.enums.trading import OrderSide, OrderStatus, OrderType, TradingSignal
from app.domain.models.order import Order
from app.domain.models.portfolio import Portfolio


@pytest.mark.anyio
async def test_execution_agent_paper_routing(db_session, mocker):
    portfolio_id = uuid.uuid4()
    strategy_id = uuid.uuid4()

    # 1. Setup mock paper portfolio
    portfolio = Portfolio(
        id=portfolio_id,
        user_id=uuid.uuid4(),
        name="Paper Portfolio",
        exchange="binance",
        is_paper_trading=True,
        quote_currency="USDT",
        available_balance=Decimal("10000.0"),
        total_value_usdt=Decimal("10000.0"),
    )
    db_session.add(portfolio)
    await db_session.commit()

    # 2. Mock BaseExchange object
    mock_exchange = AsyncMock()
    mock_exchange.exchange_id = "paper-binance"

    # PaperExchange normalized order return structure
    paper_order_id = uuid.uuid4()
    mock_exchange.create_market_order.return_value = {
        "id": str(paper_order_id),
        "symbol": "BTC/USDT",
        "side": "buy",
        "type": "market",
        "amount": 0.1,
        "filled": 0.1,
        "status": "filled",
    }

    # Add the corresponding Order model that PaperExchange expects to exist in DB
    order = Order(
        id=paper_order_id,
        portfolio_id=portfolio_id,
        symbol="BTC/USDT",
        exchange="binance",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        status=OrderStatus.FILLED,
        quantity=Decimal("0.1"),
        filled_quantity=Decimal("0.1"),
    )
    db_session.add(order)
    await db_session.commit()

    # 3. Setup AgentDependencies and ExecutionAgent
    deps = AgentDependencies(session=db_session, exchange=mock_exchange)
    agent = ExecutionAgent(deps)

    # 4. Construct TradingState
    state = TradingState(
        strategy_id=str(strategy_id), exchange="binance", symbols=["BTC/USDT"], timeframe="1h"
    )
    state.portfolio_id = str(portfolio_id)
    state.signal = TradingSignal.BUY
    state.confidence = 0.8
    state.available_balance = Decimal("10000.0")
    state.tickers = {"BTC/USDT": {"last": 50000.0}}

    # 5. Run Execution
    res = await agent.run(state)
    assert res["order_placed"] is True
    assert res["order_id"] == str(paper_order_id)
    assert mock_exchange.create_market_order.called
