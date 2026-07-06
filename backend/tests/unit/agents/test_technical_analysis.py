import pytest
from datetime import datetime, UTC
from sqlalchemy import select

from app.agents.interfaces.base import AgentDependencies
from app.agents.nodes.technical_node import TechnicalAgent
from app.agents.graph.state import TradingState
from app.domain.models.market_data import TechnicalIndicator


@pytest.mark.anyio
async def test_technical_agent_run_and_persist(db_session):
    # 1. Setup AgentDependencies and TechnicalAgent
    deps = AgentDependencies(session=db_session)
    agent = TechnicalAgent(deps)

    # 2. Mock OHLCV data (needs enough candles for 14/20/50 period indicators to calculate)
    ohlcv_data = []
    for i in range(60):
        base_price = 30000.0 + i * 10.0
        ohlcv_data.append(
            {
                "timestamp": datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC).timestamp() * 1000
                + i * 60000,
                "open": base_price,
                "high": base_price + 5.0,
                "low": base_price - 5.0,
                "close": base_price + 2.0,
                "volume": 100.0 + i,
            }
        )

    # 3. Construct TradingState
    state = TradingState(
        strategy_id="test-strategy", exchange="binance", symbols=["BTC/USDT"], timeframe="1m"
    )
    state.ohlcv = {"BTC/USDT": ohlcv_data}

    # 4. Run agent
    res = await agent.run(state)
    assert "indicators" in res
    assert "BTC/USDT" in res["indicators"]

    analysis = res["indicators"]["BTC/USDT"]
    assert analysis["rsi"] > 0.0
    assert analysis["ema_20"] > 0.0
    assert analysis["ema_50"] > 0.0
    assert analysis["bb_upper"] > 0.0
    assert analysis["bb_middle"] > 0.0
    assert analysis["bb_lower"] > 0.0

    # 5. Verify database storage
    stmt = select(TechnicalIndicator).where(TechnicalIndicator.symbol == "BTC/USDT")
    db_res = await db_session.execute(stmt)
    db_indicator = db_res.scalars().first()
    assert db_indicator is not None
    assert float(db_indicator.rsi) == float(analysis["rsi"])
    assert float(db_indicator.ema_20) == float(analysis["ema_20"])
