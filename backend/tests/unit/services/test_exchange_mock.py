from unittest.mock import AsyncMock
import ccxt.async_support as ccxt
import pytest

from app.core.exceptions import ExchangeError
from app.infrastructure.exchange.binance import BinanceExchange


@pytest.mark.anyio
async def test_binance_exchange_fetch_ticker():
    # Mock CCXT client
    mock_ccxt = AsyncMock()
    mock_ccxt.fetch_ticker.return_value = {
        "symbol": "BTC/USDT",
        "bid": 50000.0,
        "ask": 50010.0,
        "last": 50005.0,
        "baseVolume": 1000.0,
        "percentage": 1.5,
    }

    adapter = BinanceExchange()
    adapter._ccxt = mock_ccxt
    ticker = await adapter.fetch_ticker("BTC/USDT")

    assert ticker["bid"] == 50000.0
    assert ticker["ask"] == 50010.0
    assert ticker["last"] == 50005.0
    mock_ccxt.fetch_ticker.assert_called_once_with("BTC/USDT")


@pytest.mark.anyio
async def test_binance_exchange_error_handling():
    mock_ccxt = AsyncMock()
    mock_ccxt.fetch_ticker.side_effect = ccxt.AuthenticationError("Invalid API Key")

    adapter = BinanceExchange()
    adapter._ccxt = mock_ccxt

    with pytest.raises(ExchangeError) as exc_info:
        await adapter.fetch_ticker("BTC/USDT")

    assert exc_info.value.code == "AUTH_ERROR"
