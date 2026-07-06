import pytest
from unittest.mock import AsyncMock
from sqlalchemy import select

from app.agents.interfaces.base import AgentDependencies
from app.agents.nodes.market_node import MarketAgent
from app.agents.graph.state import TradingState
from app.domain.models.market_data import MarketTicker, OrderBookSnapshot


@pytest.mark.anyio
async def test_market_agent_run_and_persist(db_session, mocker):
    # 1. Mock exchange calls
    mock_exchange = AsyncMock()
    mock_exchange.exchange_id = "binance"
    mock_exchange.fetch_ticker.return_value = {
        "symbol": "BTC/USDT",
        "timestamp": 1625097600000,
        "bid": 30000.0,
        "ask": 30005.0,
        "last": 30002.0,
        "baseVolume": 100.0,
        "percentage": 1.5,
        "high": 31000.0,
        "low": 29000.0,
    }
    mock_exchange.fetch_ohlcv.return_value = [
        [1625097600000, 30000.0, 30100.0, 29900.0, 30050.0, 10.0]
    ]
    mock_exchange.fetch_order_book.return_value = {
        "bids": [[30000.0, 1.5]],
        "asks": [[30005.0, 2.0]],
    }

    # Mock ws_manager broadcast methods
    mock_ws = mocker.patch(
        "app.agents.nodes.market_node.ws_manager.broadcast_channel", new_callable=AsyncMock
    )
    mocker.patch("app.services.market_data.market_data_service.get_exchange", return_value=mock_exchange)

    # 2. Setup AgentDependencies and MarketAgent
    deps = AgentDependencies(session=db_session, exchange=mock_exchange)
    agent = MarketAgent(deps)

    # 3. Construct TradingState
    state = TradingState(
        strategy_id="test-strategy", exchange="binance", symbols=["BTC/USDT"], timeframe="1h"
    )

    # 4. Run agent
    res = await agent.run(state)
    assert "ohlcv" in res
    assert "tickers" in res
    assert "order_book" in res

    # 5. Verify database storage
    # Ticker should be synced
    stmt_ticker = select(MarketTicker).where(MarketTicker.symbol == "BTC/USDT")
    res_ticker = await db_session.execute(stmt_ticker)
    ticker = res_ticker.scalars().first()
    assert ticker is not None
    assert float(ticker.last) == 30002.0

    # OrderBookSnapshot should be saved
    stmt_snapshot = select(OrderBookSnapshot).where(OrderBookSnapshot.symbol == "BTC/USDT")
    res_snapshot = await db_session.execute(stmt_snapshot)
    snapshot = res_snapshot.scalars().first()
    assert snapshot is not None
    assert snapshot.bids == [[30000.0, 1.5]]
    assert snapshot.asks == [[30005.0, 2.0]]

    # WebSocket broadcasts should be triggered
    assert mock_ws.call_count == 2


@pytest.mark.anyio
async def test_market_agent_replay_and_caching(db_session, mocker):
    import arrow
    from decimal import Decimal
    from datetime import UTC
    from app.domain.models.strategy import Strategy

    from app.domain.models.market_data import OHLCV, OrderBookSnapshot

    replay_time = arrow.get("2026-07-06T12:00:00Z").datetime
    strategy_id = uuid.uuid4() if "uuid" in globals() else uuid_lib.uuid4() if "uuid_lib" in globals() else None
    if strategy_id is None:
        import uuid as uuid_lib
        strategy_id = uuid_lib.uuid4()

    # 1. Create a strategy config with replay timestamp
    strategy = Strategy(
        id=strategy_id,
        user_id=uuid_lib.uuid4(),
        name="Replay Strategy",
        exchange="binance",
        symbols=["BTC/USDT"],
        config={"replay_timestamp": "2026-07-06T12:00:00Z"},
    )
    db_session.add(strategy)

    # 2. Insert historical OHLCV and Order Book Snapshot before the replay time
    ohlcv_record = OHLCV(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        timestamp=arrow.get("2026-07-06T11:00:00Z").datetime,
        open=Decimal("50000.0"),
        high=Decimal("50500.0"),
        low=Decimal("49900.0"),
        close=Decimal("50200.0"),
        volume=Decimal("5.0"),
    )
    db_session.add(ohlcv_record)

    book_record = OrderBookSnapshot(
        exchange="binance",
        symbol="BTC/USDT",
        timestamp=arrow.get("2026-07-06T11:30:00Z").datetime,
        bids=[[50190.0, 1.2]],
        asks=[[50210.0, 1.8]],
    )
    db_session.add(book_record)
    await db_session.commit()

    # 3. Setup AgentDependencies with mocked exchange (to assert it is NOT called during replay)
    mock_exchange = AsyncMock()
    mock_ws = mocker.patch(
        "app.agents.nodes.market_node.ws_manager.broadcast_channel", new_callable=AsyncMock
    )

    deps = AgentDependencies(session=db_session, exchange=mock_exchange)
    agent = MarketAgent(deps)

    state = TradingState(
        strategy_id=str(strategy_id), exchange="binance", symbols=["BTC/USDT"], timeframe="1h"
    )

    # 4. Run Agent in Replay Mode
    res = await agent.run(state)

    # Verify return structure matches historical database values
    assert "ohlcv" in res
    assert res["ohlcv"]["BTC/USDT"][0]["close"] == 50200.0
    assert res["tickers"]["BTC/USDT"]["last"] == 50200.0
    assert res["order_book"]["BTC/USDT"]["bids"] == [[50190.0, 1.2]]

    # Ensure no exchange calls were made
    assert not mock_exchange.fetch_ticker.called
    assert not mock_exchange.fetch_ohlcv.called
    assert not mock_exchange.fetch_order_book.called

    # Ensure no WebSocket broadcasts occurred
    assert mock_ws.call_count == 0

