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
    mocker.patch(
        "app.services.market_data.market_data_service.get_exchange", return_value=mock_exchange
    )

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
