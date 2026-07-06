import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import select

from app.agents.graph.state import TradingState
from app.agents.interfaces.base import AgentDependencies
from app.agents.nodes.memory_node import MemoryAgent
from app.domain.models.memory import LongTermMemory


@pytest.mark.anyio
async def test_memory_agent_run_and_save(db_session, mocker):
    strategy_id = uuid.uuid4()
    run_id = str(uuid.uuid4())

    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.lrange.return_value = []
    mock_redis.lpush.return_value = 1

    # Mock EmbeddingService
    mock_embed = MagicMock()
    mock_embed.embed_query = AsyncMock(return_value=[0.1] * 1536)
    mocker.patch("app.services.embedding.embedding_service.EmbeddingService", return_value=mock_embed)

    # Initialize MemoryAgent
    deps = AgentDependencies(session=db_session, redis=mock_redis)
    agent = MemoryAgent(deps)

    # 1. Test save_context
    outcome = {
        "symbols": ["BTC/USDT"],
        "timeframe": "1h",
        "signal": "buy",
        "confidence": 0.9,
        "reasoning": "RSI oversold",
        "news_summary": "Positive ETF inflows",
        "indicators_summary": "RSI 25, EMA 200",
        "performance_summary": "Target hit",
    }

    class MockReflection:
        summary = "Great entry timing"
        lessons_learned = ["Follow discipline"]

    reflection = MockReflection()

    await agent.save_context(
        strategy_id=str(strategy_id), run_id=run_id, outcome=outcome, reflection=reflection
    )

    # Verify model is persisted in DB
    stmt = select(LongTermMemory).where(LongTermMemory.run_id == run_id)
    db_res = await db_session.execute(stmt)
    mem = db_res.scalars().first()
    assert mem is not None
    assert mem.symbol == "BTC/USDT"
    assert mem.signal == "buy"
    assert mem.confidence == 0.9
    assert mem.reasoning == "RSI oversold"
    assert mem.news_summary == "Positive ETF inflows"
    assert mem.indicators_summary == "RSI 25, EMA 200"
    assert mem.performance_summary == "Target hit"
    assert mem.lessons_learned == "Follow discipline"
    assert mem.reflection == "Great entry timing"
    assert len(mem.embedding) == 1536

    # 2. Test load_context (run node)
    state = TradingState(
        strategy_id=str(strategy_id), exchange="binance", symbols=["BTC/USDT"], timeframe="1h"
    )

    res = await agent.run(state)
    assert "memory_context" in res
    ctx = res["memory_context"]
    assert len(ctx.past_reflections) == 1
    assert ctx.past_reflections[0]["run_id"] == run_id
