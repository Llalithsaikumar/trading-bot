import uuid
from decimal import Decimal
from unittest.mock import AsyncMock
import pytest

from app.domain.enums.trading import PositionSide
from app.domain.models.portfolio import Portfolio, Position
from app.infrastructure.exchange.binance import BinanceExchange
from app.infrastructure.exchange.paper import PaperExchange


@pytest.mark.anyio
async def test_paper_exchange_rest_methods(db_session, mocker):
    portfolio_id = uuid.uuid4()

    mock_delegate = AsyncMock()
    mocker.patch("app.infrastructure.exchange.paper.get_exchange", return_value=mock_delegate)

    # 1. Create a paper trading portfolio
    portfolio = Portfolio(
        id=portfolio_id,
        user_id=uuid.uuid4(),
        name="Test Paper Portfolio",
        exchange="binance",
        is_paper_trading=True,
        quote_currency="USDT",
        available_balance=Decimal("10000.0"),
        total_value_usdt=Decimal("10000.0"),
    )
    db_session.add(portfolio)

    pos = Position(
        portfolio_id=portfolio_id,
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.5"),
        entry_price=Decimal("50000.0"),
        current_price=Decimal("50000.0"),
        unrealized_pnl=Decimal("0.0"),
        unrealized_pnl_pct=Decimal("0.0"),
    )
    db_session.add(pos)
    await db_session.commit()

    # 2. Instantiate PaperExchange
    exchange = PaperExchange(portfolio_id, db_session, exchange_id="binance")

    # 3. Test fetch_balance
    balance = await exchange.fetch_balance()
    assert balance["USDT"]["free"] == 10000.0
    assert balance["free"]["USDT"] == 10000.0

    # 4. Test fetch_positions
    positions = await exchange.fetch_positions()
    assert len(positions) == 1
    assert positions[0]["symbol"] == "BTC/USDT"
    assert positions[0]["contracts"] == 0.5

    # 5. Test create_limit_order
    mocker.patch(
        "app.services.paper_trading.engine.PaperTradingEngine.get_market_price",
        return_value=Decimal("50000.0"),
    )

    order_res = await exchange.create_limit_order(
        symbol="BTC/USDT", side="sell", amount=0.1, price=51000.0
    )
    assert order_res["status"] == "open"
    assert order_res["amount"] == 0.1
    assert order_res["price"] == 51000.0

    # 6. Test cancel_order
    cancel_res = await exchange.cancel_order(order_res["id"], "BTC/USDT")
    assert cancel_res["status"] == "cancelled"

    # 7. Test fetch_orders
    orders = await exchange.fetch_orders()
    assert len(orders) == 1
    assert orders[0]["id"] == order_res["id"]


@pytest.mark.anyio
async def test_binance_exchange_fetch_orders(mocker):
    mock_ccxt = AsyncMock()
    mock_ccxt.fetch_orders.return_value = [
        {"id": "123", "symbol": "BTC/USDT", "side": "buy", "status": "closed"}
    ]

    adapter = BinanceExchange()
    adapter._ccxt = mock_ccxt

    orders = await adapter.fetch_orders("BTC/USDT", limit=10)
    assert len(orders) == 1
    assert orders[0]["id"] == "123"
    mock_ccxt.fetch_orders.assert_called_once_with("BTC/USDT", since=None, limit=10, params={})
