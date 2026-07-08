import pytest
from decimal import Decimal
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

from app.agents.graph.state import TradingState, PredictionInsight
from app.agents.interfaces.base import AgentDependencies
from app.agents.nodes.insight_node import InsightAgent
from app.agents.graph.builder import build_trading_graph


@pytest.mark.anyio
async def test_insight_agent_run(db_session, mocker):
    # Mock PolymarketService
    mock_markets = [
        MagicMock(
            condition_id="c1",
            question="Will Bitcoin hit $100k?",
            probability=0.60,
            liquidity=Decimal("1000.00"),
            volume=Decimal("5000.00"),
            end_date=datetime.now(UTC),
            active=True,
        ),
        MagicMock(
            condition_id="c2",
            question="Will Solana hit $500?",
            probability=0.30,
            liquidity=Decimal("2000.00"),
            volume=Decimal("8000.00"),
            end_date=datetime.now(UTC),
            active=True,
        ),
    ]

    mock_service = MagicMock()
    mock_service.fetch_crypto_markets = AsyncMock(return_value=mock_markets)
    mocker.patch("app.agents.nodes.insight_node.PolymarketService", return_value=mock_service)

    deps = AgentDependencies(session=db_session)
    agent = InsightAgent(deps)

    state = TradingState(
        strategy_id="test-strategy", exchange="binance", symbols=["BTC/USDT"], timeframe="1h"
    )

    res = await agent.run(state)

    assert "prediction_insights" in res
    assert "prediction_sentiment" in res

    insights = res["prediction_insights"]
    sentiment = res["prediction_sentiment"]

    assert len(insights) == 2
    assert insights[0].market_id == "c1"
    assert insights[0].probability == 0.60
    assert insights[1].market_id == "c2"
    assert insights[1].probability == 0.30

    # Bullish (>0.55): c1 (0.60) -> 1
    # Bearish (<0.45): c2 (0.30) -> 1
    # Signal strength: (1 - 1) / 2 = 0.0
    assert sentiment.bullish_count == 1
    assert sentiment.bearish_count == 1
    assert sentiment.avg_probability == pytest.approx(0.45)
    assert sentiment.signal_strength == 0.0
    assert sentiment.total_liquidity == Decimal("3000.00")


@pytest.mark.anyio
async def test_insight_agent_idempotency():
    deps = AgentDependencies()
    agent = InsightAgent(deps)

    state = TradingState(
        strategy_id="test-strategy", exchange="binance", symbols=["BTC/USDT"], timeframe="1h"
    )

    # Pre-populate insights
    existing_insight = PredictionInsight(
        market_id="ex1",
        question="Will Bitcoin hit $100k?",
        probability=0.7,
        liquidity=Decimal("100"),
        volume=Decimal("500"),
    )
    state.prediction_insights = [existing_insight]

    res = await agent.run(state)
    assert res["prediction_insights"] == [existing_insight]


@pytest.mark.anyio
async def test_graph_compiles_with_insight_node():
    deps = AgentDependencies()
    graph = build_trading_graph(deps)
    assert graph is not None
