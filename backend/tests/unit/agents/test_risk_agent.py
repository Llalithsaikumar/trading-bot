from datetime import UTC, datetime
from decimal import Decimal
import uuid
import pytest

from app.agents.graph.state import PortfolioMetrics, TradingState
from app.agents.interfaces.base import AgentDependencies
from app.agents.nodes.risk_node import RiskAgent
from app.domain.enums.trading import TradingSignal
from app.domain.models.portfolio import EquityPoint, Portfolio


@pytest.mark.anyio
async def test_risk_agent_sizing_and_rules(db_session):
    portfolio_id = uuid.uuid4()

    # 1. Setup portfolio & positions
    portfolio = Portfolio(
        id=portfolio_id,
        user_id=uuid.uuid4(),
        name="Risk Test Portfolio",
        exchange="binance",
        is_paper_trading=True,
        quote_currency="USDT",
        available_balance=Decimal("10000.0"),
        total_value_usdt=Decimal("10000.0"),
    )
    db_session.add(portfolio)

    # Add 1 equity point to start history
    db_session.add(
        EquityPoint(
            portfolio_id=portfolio_id,
            timestamp=datetime.now(UTC),
            equity=Decimal("10000.0"),
            balance=Decimal("10000.0"),
            realized_pnl=Decimal("0.0"),
            unrealized_pnl=Decimal("0.0"),
            daily_pnl=Decimal("0.0"),
        )
    )
    await db_session.commit()

    # 2. Setup Agent & Dependencies
    deps = AgentDependencies(session=db_session)
    agent = RiskAgent(deps)

    # 3. Test Trade - Sizing
    state = TradingState(
        strategy_id="test-strategy", exchange="binance", symbols=["BTC/USDT"], timeframe="1h"
    )
    state.portfolio_id = str(portfolio_id)
    state.signal = TradingSignal.BUY
    state.confidence = 0.8
    state.suggested_entry = Decimal("50000.0")
    state.suggested_stop_loss = Decimal("49000.0")  # 2% unit risk
    state.suggested_take_profit = Decimal("53000.0")
    state.available_balance = Decimal("10000.0")
    state.tickers = {"BTC/USDT": {"last": 50000.0}}

    state.portfolio_metrics = PortfolioMetrics(
        total_value_usdt=Decimal("10000.0"),
        available_margin=Decimal("10000.0"),
        win_rate=0.5,
        exposure=Decimal("0.0"),
    )

    res = await agent.run(state)
    assert res["risk_approved"] is True
    assert state.suggested_size is not None
    assert state.suggested_size > 0

    # 4. Test Rule - 3 Consecutive Losses
    # Insert 3 negative closed trades (resulting in 3 consecutive losses)
    db_session.add(
        EquityPoint(
            portfolio_id=portfolio_id,
            timestamp=datetime.now(UTC),
            equity=Decimal("10000.0"),
            balance=Decimal("10000.0"),
            realized_pnl=Decimal("500.0"),
            unrealized_pnl=Decimal("0.0"),
            daily_pnl=Decimal("0.0"),
        )
    )
    db_session.add(
        EquityPoint(
            portfolio_id=portfolio_id,
            timestamp=datetime.now(UTC),
            equity=Decimal("9900.0"),
            balance=Decimal("9900.0"),
            realized_pnl=Decimal("400.0"),  # Loss of 100
            unrealized_pnl=Decimal("0.0"),
            daily_pnl=Decimal("0.0"),
        )
    )
    db_session.add(
        EquityPoint(
            portfolio_id=portfolio_id,
            timestamp=datetime.now(UTC),
            equity=Decimal("9800.0"),
            balance=Decimal("9800.0"),
            realized_pnl=Decimal("300.0"),  # Loss of 100
            unrealized_pnl=Decimal("0.0"),
            daily_pnl=Decimal("0.0"),
        )
    )
    db_session.add(
        EquityPoint(
            portfolio_id=portfolio_id,
            timestamp=datetime.now(UTC),
            equity=Decimal("9700.0"),
            balance=Decimal("9700.0"),
            realized_pnl=Decimal("200.0"),  # Loss of 100
            unrealized_pnl=Decimal("0.0"),
            daily_pnl=Decimal("0.0"),
        )
    )
    await db_session.commit()

    res = await agent.run(state)
    assert res["risk_approved"] is False
    assert any("consecutive losses" in v.message for v in res["risk_violations"])
