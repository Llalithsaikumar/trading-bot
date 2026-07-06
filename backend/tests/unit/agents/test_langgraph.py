import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.graph.builder import TradingGraphBuilder
from app.agents.interfaces.base import AgentDependencies
from app.agents.graph.state import TradingState, MemoryContext, MarketSentiment, PortfolioMetrics
from app.domain.enums.trading import TradingSignal


def test_graph_compilation():
    deps = AgentDependencies()
    builder = TradingGraphBuilder(deps)
    graph = builder.build()
    assert graph is not None


@pytest.mark.anyio
async def test_langgraph_execution_routing(mocker):
    # Mock all agent run methods to return simple state additions
    mocker.patch(
        "app.agents.nodes.memory_node.MemoryAgent.run",
        return_value={"memory_context": MemoryContext()},
    )
    mocker.patch(
        "app.agents.nodes.market_node.MarketAgent.run",
        return_value={"tickers": {"BTC/USDT": {"last": 50000.0}}, "ohlcv": {"BTC/USDT": []}},
    )
    mocker.patch(
        "app.agents.nodes.news_node.NewsAgent.run",
        return_value={
            "news_items": [],
            "sentiment": MarketSentiment(overall_score=0.5, label="neutral"),
        },
    )
    mocker.patch(
        "app.agents.nodes.technical_node.TechnicalAgent.run",
        return_value={"indicators": {"BTC/USDT": {}}},
    )
    mocker.patch(
        "app.agents.nodes.portfolio_node.PortfolioAgent.run",
        return_value={
            "available_balance": 10000.0,
            "open_positions": [],
            "portfolio_metrics": PortfolioMetrics(),
        },
    )
    mocker.patch(
        "app.agents.nodes.decision_node.DecisionAgent.run",
        return_value={"signal": TradingSignal.BUY, "confidence": 0.8, "reasoning": "RSI low"},
    )

    # We want to test the execution routing under risk_approved=True
    mocker.patch("app.agents.nodes.risk_node.RiskAgent.run", return_value={"risk_approved": True})

    mock_exec = mocker.patch(
        "app.agents.nodes.execution_node.ExecutionAgent.run", return_value={"order_placed": True}
    )
    mock_reflect = mocker.patch(
        "app.agents.nodes.reflection_node.ReflectionAgent.run", return_value={}
    )

    deps = AgentDependencies()
    builder = TradingGraphBuilder(deps)
    graph = builder.build()

    state = TradingState(
        strategy_id=str(uuid.uuid4()),
        exchange="binance",
        symbols=["BTC/USDT"],
        timeframe="1h",
        portfolio_id=str(uuid.uuid4()),
    )

    result = await graph.ainvoke(state)

    # Assert execution and reflection were both invoked
    mock_exec.assert_called_once()
    mock_reflect.assert_called_once()
    assert result["order_placed"] is True
