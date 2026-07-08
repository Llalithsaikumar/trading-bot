import uuid
from decimal import Decimal

import pytest

from app.agents.interfaces.base import AgentDependencies
from app.agents.nodes.trade_reflection_node import TradeReflectionAgent
from app.domain.models.memory import LongTermMemory
from app.domain.models.order import Order
from app.domain.models.strategy import Strategy, StrategyExecution


@pytest.mark.anyio
async def test_trade_reflection_agent_success(db_session):
    strategy_id = uuid.uuid4()
    order_id = uuid.uuid4()
    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"

    # 1. Create Strategy
    strategy = Strategy(
        id=strategy_id,
        user_id=uuid.uuid4(),
        name="Test strategy",
        exchange="binance",
        symbols=["BTC/USDT"],
        timeframe="1h",
        status="active",
    )
    db_session.add(strategy)

    # 2. Create StrategyExecution
    execution = StrategyExecution(
        strategy_id=strategy_id,
        run_id=run_id,
        status="success",
        signal="buy",
        reasoning="bullish signals on RSI",
        duration_ms=100,
    )
    db_session.add(execution)

    # 3. Create LongTermMemory context
    mem_record = LongTermMemory(
        strategy_id=strategy_id,
        run_id=run_id,
        symbol="BTC/USDT",
        signal="buy",
        confidence=0.8,
        reasoning="bullish signals on RSI",
        news_summary="Positive regulatory updates",
        indicators_summary="RSI: 30",
        performance_summary="good",
        embedding_text="initial decision context",
        embedding=[0.0] * 1536,
    )
    db_session.add(mem_record)

    # 4. Create Order
    order = Order(
        id=order_id,
        portfolio_id=uuid.uuid4(),
        exchange_order_id="PAPER-12345",
        symbol="BTC/USDT",
        exchange="binance",
        side="buy",
        order_type="market",
        status="filled",
        quantity=Decimal("1.0"),
        average_fill_price=Decimal("50000.0"),
        fee=Decimal("10.0"),
        fee_currency="USDT",
        strategy_id=strategy_id,
        agent_reasoning="bullish signals on RSI",
    )
    db_session.add(order)
    await db_session.commit()

    # 5. Instantiate TradeReflectionAgent
    deps = AgentDependencies(session=db_session)
    agent = TradeReflectionAgent(deps)

    # Reflect on trade
    result = await agent.reflect_on_trade(order_id, Decimal("500.0"))
    assert result is not None
    assert "prediction_correct" in result
    assert "lessons_learned" in result

    # Check if a reflection memory record was saved
    from sqlalchemy import select

    stmt = (
        select(LongTermMemory)
        .where(LongTermMemory.strategy_id == strategy_id, LongTermMemory.run_id == run_id)
        .order_by(LongTermMemory.created_at.desc())
    )
    result_mems = await db_session.execute(stmt)
    mems = result_mems.scalars().all()
    # There should be 2 memories: the initial one and the trade reflection one
    assert len(mems) == 2
    assert mems[0].reflection != ""

    # Check updated strategy confidence
    await db_session.refresh(strategy)
    assert strategy.config is not None
    assert "confidence" in strategy.config
    assert (
        strategy.config["confidence"] == 0.5
    )  # default stub_reflection returns no_change (0.5 + 0.0)
