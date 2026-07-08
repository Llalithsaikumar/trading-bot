"""Paper trading exchange adapter mapping CCXT BaseExchange methods to the PaperTradingEngine."""

from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any
import uuid
from sqlalchemy import select

from app.domain.enums.trading import OrderSide, OrderStatus, OrderType, PositionSide
from app.domain.models.order import Order
from app.domain.models.portfolio import Portfolio, Position
from app.domain.schemas.trading import OrderCreate
from app.infrastructure.exchange.base import BaseExchange
from app.infrastructure.exchange.factory import get_exchange
from app.infrastructure.repositories.portfolio_repository import PortfolioRepository
from app.services.paper_trading.engine import PaperTradingEngine


class PaperExchange(BaseExchange):
    """
    PaperExchange adapts PaperTradingEngine database operations to the BaseExchange interface.
    Public market data (ticker, OHLCV, order book) is delegated to a CCXT-backed public exchange client.
    """

    @property
    def exchange_id(self) -> str:
        return f"paper-{self._delegate_id}"

    def __init__(
        self,
        portfolio_id: uuid.UUID,
        session: Any,
        exchange_id: str = "binance",
    ) -> None:
        self._portfolio_id = portfolio_id
        self._session = session
        self._delegate_id = exchange_id.lower()
        self._public_exchange = get_exchange(self._delegate_id)
        self._engine = PaperTradingEngine(session)

    # ── REST ────────────────────────────────────────────────────────────────────

    async def fetch_balance(self) -> dict[str, Any]:
        portfolio_repo = PortfolioRepository(self._session)
        portfolio = await portfolio_repo.get_with_positions(self._portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {self._portfolio_id} not found")

        balance_usdt = float(portfolio.available_balance)
        total_usdt = float(portfolio.total_value_usdt)
        used_usdt = total_usdt - balance_usdt

        return {
            "info": {},
            "USDT": {"free": balance_usdt, "used": used_usdt, "total": total_usdt},
            "free": {"USDT": balance_usdt},
            "used": {"USDT": used_usdt},
            "total": {"USDT": total_usdt},
        }

    async def fetch_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        portfolio_repo = PortfolioRepository(self._session)
        portfolio = await portfolio_repo.get_with_positions(self._portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {self._portfolio_id} not found")

        positions = []
        for pos in portfolio.positions:
            if symbol and pos.symbol != symbol:
                continue
            positions.append(
                {
                    "info": {},
                    "symbol": pos.symbol,
                    "side": "long" if pos.side == PositionSide.LONG else "short",
                    "contracts": float(pos.quantity),
                    "entryPrice": float(pos.entry_price),
                    "unrealizedPnl": float(pos.unrealized_pnl),
                    "percentage": float(pos.unrealized_pnl_pct * 100),
                }
            )
        return positions

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
        since: int | None = None,
    ) -> list[list[Any]]:
        return await self._public_exchange.fetch_ohlcv(symbol, timeframe, limit=limit, since=since)

    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        portfolio_repo = PortfolioRepository(self._session)
        portfolio = await portfolio_repo.get_with_positions(self._portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {self._portfolio_id} not found")

        payload = OrderCreate(
            portfolio_id=self._portfolio_id,
            symbol=symbol,
            side=OrderSide(side.lower()),
            order_type=OrderType.MARKET,
            quantity=Decimal(str(amount)),
            price=None,
        )
        order = await self._engine.execute_order(portfolio, payload)
        return self._normalize_order(order)

    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        portfolio_repo = PortfolioRepository(self._session)
        portfolio = await portfolio_repo.get_with_positions(self._portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {self._portfolio_id} not found")

        payload = OrderCreate(
            portfolio_id=self._portfolio_id,
            symbol=symbol,
            side=OrderSide(side.lower()),
            order_type=OrderType.LIMIT,
            quantity=Decimal(str(amount)),
            price=Decimal(str(price)),
        )
        order = await self._engine.execute_order(portfolio, payload)
        return self._normalize_order(order)

    async def cancel_order(self, order_id: str, symbol: str) -> dict[str, Any]:
        try:
            uid = uuid.UUID(order_id)
        except ValueError:
            raise ValueError(f"Invalid order ID: {order_id}")

        order = await self._session.get(Order, uid)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        if order.status in (OrderStatus.OPEN, OrderStatus.PENDING):
            order.status = OrderStatus.CANCELLED
            self._session.add(order)
            await self._session.flush()

        return self._normalize_order(order)

    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        return await self._public_exchange.fetch_ticker(symbol)

    async def fetch_order_book(self, symbol: str, limit: int = 20) -> dict[str, Any]:
        return await self._public_exchange.fetch_order_book(symbol, limit)

    async def fetch_funding_rate(self, symbol: str) -> dict[str, Any]:
        return await self._public_exchange.fetch_funding_rate(symbol)

    async def fetch_funding_rates(self, symbols: list[str] | None = None) -> dict[str, Any]:
        return await self._public_exchange.fetch_funding_rates(symbols)

    async def fetch_orders(
        self,
        symbol: str | None = None,
        since: int | None = None,
        limit: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        stmt = select(Order).where(Order.portfolio_id == self._portfolio_id)
        if symbol:
            stmt = stmt.where(Order.symbol == symbol)
        stmt = stmt.order_by(Order.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        orders = result.scalars().all()
        return [self._normalize_order(o) for o in orders]

    # ── WebSocket async generators ──────────────────────────────────────────────

    async def watch_ticker(self, symbol: str) -> AsyncIterator[dict[str, Any]]:
        async for update in self._public_exchange.watch_ticker(symbol):
            yield update

    async def watch_ohlcv(
        self, symbol: str, timeframe: str = "1m"
    ) -> AsyncIterator[list[list[Any]]]:
        async for update in self._public_exchange.watch_ohlcv(symbol, timeframe):
            yield update

    async def watch_order_book(self, symbol: str, limit: int = 20) -> AsyncIterator[dict[str, Any]]:
        async for update in self._public_exchange.watch_order_book(symbol, limit):
            yield update

    async def watch_trades(self, symbol: str) -> AsyncIterator[list[dict[str, Any]]]:
        async for update in self._public_exchange.watch_trades(symbol):
            yield update

    async def watch_balance(self) -> AsyncIterator[dict[str, Any]]:
        raise NotImplementedError("watch_balance not supported on PaperExchange")

    async def watch_orders(self, symbol: str | None = None) -> AsyncIterator[list[dict[str, Any]]]:
        raise NotImplementedError("watch_orders not supported on PaperExchange")

    async def close(self) -> None:
        pass

    def _val(self, obj: Any) -> str | None:
        if obj is None:
            return None
        if hasattr(obj, "value"):
            return str(obj.value)
        return str(obj)

    def _normalize_order(self, order: Order) -> dict[str, Any]:
        return {
            "id": str(order.id),
            "clientOrderId": str(order.exchange_order_id),
            "timestamp": int(order.created_at.timestamp() * 1000) if order.created_at else None,
            "datetime": order.created_at.isoformat() if order.created_at else None,
            "lastTradeTimestamp": None,
            "symbol": order.symbol,
            "type": self._val(order.order_type),
            "timeInForce": self._val(order.time_in_force),
            "side": self._val(order.side),
            "price": float(order.price) if order.price else None,
            "average": float(order.average_fill_price) if order.average_fill_price else None,
            "amount": float(order.quantity),
            "filled": float(order.filled_quantity),
            "remaining": float(order.quantity - order.filled_quantity),
            "status": self._val(order.status),
            "fee": {
                "cost": float(order.fee) if order.fee else None,
                "currency": order.fee_currency or "USDT",
            },
            "info": {},
        }
