import uuid
from unittest.mock import AsyncMock

import pytest

from app.agents.graph.builder import TradingGraphBuilder
from app.agents.graph.state import MarketSentiment, MemoryContext, PortfolioMetrics, TradingState
from app.agents.interfaces.base import AgentDependencies
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
        "app.agents.nodes.insight_node.InsightAgent.run",
        return_value={"prediction_insights": [], "prediction_sentiment": {}},
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


@pytest.mark.anyio
async def test_langgraph_idempotency_and_checkpoints(mocker):
    # Setup state that has ALREADY completed decision and execution
    from app.agents.nodes.decision_node import DecisionAgent
    from app.domain.enums.trading import TradingSignal

    mock_decide = mocker.patch(
        "app.agents.nodes.decision_node.DecisionAgent._run_decision",
        new_callable=AsyncMock,
    )

    deps = AgentDependencies()
    agent = DecisionAgent(deps)

    state = TradingState(
        strategy_id=str(uuid.uuid4()),
        exchange="binance",
        symbols=["BTC/USDT"],
        timeframe="1h",
        portfolio_id=str(uuid.uuid4()),
    )
    # Inject signal into state to trigger DecisionAgent's idempotency check
    state.signal = TradingSignal.BUY
    state.confidence = 0.95
    state.reasoning = "Cached Signal"

    res = await agent.run(state)

    # Assert that DecisionAgent returned the cached signal without executing _run_decision
    assert res["signal"] == TradingSignal.BUY
    assert res["confidence"] == 0.95
    assert not mock_decide.called

    # Mock node execution to test checkpoint state retrieval
    mocker.patch(
        "app.agents.nodes.memory_node.MemoryAgent.run",
        return_value={"memory_context": MemoryContext(context_key="loaded")},
    )
    mocker.patch(
        "app.agents.nodes.market_node.MarketAgent.run", return_value={"tickers": {}, "ohlcv": {}}
    )
    mocker.patch("app.agents.nodes.news_node.NewsAgent.run", return_value={})
    mocker.patch("app.agents.nodes.technical_node.TechnicalAgent.run", return_value={})
    mocker.patch("app.agents.nodes.insight_node.InsightAgent.run", return_value={})
    mocker.patch("app.agents.nodes.portfolio_node.PortfolioAgent.run", return_value={})
    mocker.patch(
        "app.agents.nodes.decision_node.DecisionAgent.run",
        return_value={"signal": TradingSignal.NEUTRAL},
    )
    mocker.patch("app.agents.nodes.risk_node.RiskAgent.run", return_value={"risk_approved": False})
    mocker.patch("app.agents.nodes.reflection_node.ReflectionAgent.run", return_value={})

    # Verify checkpointer compilation is successful and config mapping works
    builder = TradingGraphBuilder(deps)
    graph = builder.build()

    config = {"configurable": {"thread_id": "test-thread-id"}}
    state.signal = None  # reset signal to allow standard mock run

    result = await graph.ainvoke(state, config=config)
    assert result is not None

    # Retrieve state from checkpointer
    saved_state = await graph.aget_state(config)
    assert saved_state.values["memory_context"].context_key == "loaded"
