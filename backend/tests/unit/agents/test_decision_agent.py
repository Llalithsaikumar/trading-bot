from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.agents.graph.state import PortfolioMetrics, TradingState
from app.agents.interfaces.base import AgentDependencies
from app.agents.nodes.decision_node import DecisionAgent, TradingDecision
from app.domain.enums.trading import TradingSignal


@pytest.mark.anyio
async def test_decision_agent_prompt_and_mapping(mocker):
    # Mock LLM with structured output support
    mock_llm = MagicMock()
    mock_structured_llm = AsyncMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm

    mock_structured_llm.ainvoke.return_value = TradingDecision(
        signal="BUY",
        confidence=0.85,
        reasoning="Bullish setup with RSI support.",
        suggested_entry="50000.0",
        suggested_stop_loss="49000.0",
        suggested_take_profit="52000.0",
    )

    deps = AgentDependencies(llm=mock_llm)
    agent = DecisionAgent(deps)

    # Construct TradingState with all required input dimensions: TA, Portfolio, Risk, Market
    state = TradingState(
        strategy_id="test-strategy", exchange="binance", symbols=["BTC/USDT"], timeframe="1h"
    )
    state.available_balance = Decimal("10000.0")
    state.tickers = {"BTC/USDT": {"last": 50000.0, "bid": 49990.0, "ask": 50010.0}}
    state.indicators = {"BTC/USDT": {"rsi": 45.0, "ema_20": 49800.0}}
    state.portfolio_metrics = PortfolioMetrics(
        total_value_usdt=Decimal("10000.0"),
        available_margin=Decimal("10000.0"),
        exposure=Decimal("0.0"),
    )

    # Run decision agent
    res = await agent.run(state)

    assert res["signal"] == TradingSignal.BUY
    assert res["confidence"] == 0.85
    assert res["suggested_entry"] == Decimal("50000.0")
    assert res["suggested_stop_loss"] == Decimal("49000.0")
    assert res["suggested_take_profit"] == Decimal("52000.0")

    # Verify no execution or order placing logic was invoked
    assert mock_llm.with_structured_output.called
