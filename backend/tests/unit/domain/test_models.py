"""Unit tests for domain model instantiation and constraints."""
from __future__ import annotations

from app.domain.enums.trading import OrderSide, OrderType
from app.domain.models.order import Order


def test_order_instantiation() -> None:
    """Order can be created with required fields (no DB needed)."""
    order = Order(
        symbol="BTC/USDT",
        exchange="binance",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.001,
    )
    assert order.symbol == "BTC/USDT"
    assert order.side == OrderSide.BUY


# TODO: add model constraint tests, relationship tests
