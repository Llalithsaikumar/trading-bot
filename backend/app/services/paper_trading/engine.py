"""
Paper Trading Engine — simulates order execution against live prices.

Design principles:
- Market orders: immediate fill at spot price ± slippage + taker fee
- Limit orders: queued as OPEN; filled by background task when price crosses
- Stop/TP orders: same queuing logic, triggered on price cross
- Positions: per-symbol, per-portfolio; averaged on add, realized PnL on reduce
- Equity snapshots: recorded after every fill for PnL charting
- No live orders are ever sent to an exchange
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import select

from app.core.exceptions import ExchangeError, InsufficientBalanceError
from app.domain.enums.trading import OrderSide, OrderStatus, OrderType, PositionSide
from app.domain.models.order import Order
from app.domain.models.portfolio import EquityPoint, Portfolio, Position
from app.infrastructure.exchange import get_exchange
from app.infrastructure.repositories.order_repository import OrderRepository
from app.infrastructure.repositories.portfolio_repository import (
    EquityRepository,
    PortfolioRepository,
)
from app.services.paper_trading.fees import calc_fee
from app.services.paper_trading.slippage import SlippageCalculator, SlippageModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domain.schemas.trading import OrderCreate

_DUST = Decimal("0.000000001")  # treat quantities below this as zero


class PaperTradingEngine:
    """
    Core simulation engine.  One instance per request (stateless between calls).
    """

    def __init__(
        self,
        session: AsyncSession,
        slippage_bps: Decimal = Decimal("10"),
        use_volume_impact: bool = False,
    ) -> None:
        self._db = session
        self._order_repo = OrderRepository(session)
        self._portfolio_repo = PortfolioRepository(session)
        self._equity_repo = EquityRepository(session)
        self._slip = SlippageCalculator(
            model=SlippageModel.VOLUME_IMPACT if use_volume_impact else SlippageModel.FIXED,
            bps=slippage_bps,
        )

    # ── Price ─────────────────────────────────────────────────────────────────

    async def get_market_price(self, exchange: str, symbol: str) -> Decimal:
        """Fetch latest mid-price from the ccxt exchange (public endpoint)."""
        try:
            exc = get_exchange(exchange)
            ticker = await exc.fetch_ticker(symbol)
            raw = ticker.get("last") or ticker.get("close") or ticker.get("bid")
            if raw is None:
                raise ExchangeError(f"No price in ticker response for {symbol}")
            return Decimal(str(raw))
        except Exception as e:
            raise ExchangeError(
                f"Price fetch failed [{exchange}/{symbol}]: {e}",
                code="PRICE_FETCH_FAILED",
            ) from e

    # ── Order execution ───────────────────────────────────────────────────────

    async def execute_order(
        self,
        portfolio: Portfolio,
        payload: OrderCreate,
        market_price: Decimal | None = None,
    ) -> Order:
        """
        Simulate an order.

        Market orders are filled immediately.
        Limit / stop / take-profit orders are queued (status=OPEN) and filled
        by `process_pending_orders` when the price condition is satisfied.
        """
        if not portfolio.is_paper_trading:
            raise ValueError("PaperTradingEngine called on a live portfolio")

        if market_price is None:
            market_price = await self.get_market_price(portfolio.exchange, payload.symbol)

        order = Order(
            portfolio_id=portfolio.id,
            exchange_order_id=f"PAPER-{uuid.uuid4().hex[:12].upper()}",
            symbol=payload.symbol,
            exchange=portfolio.exchange,
            side=payload.side,
            order_type=payload.order_type,
            status=OrderStatus.PENDING,
            time_in_force=payload.time_in_force,
            quantity=payload.quantity,
            price=payload.price,
            stop_price=payload.stop_price,
            reduce_only=payload.reduce_only,
            filled_quantity=Decimal("0"),
            fee=Decimal("0"),
        )

        if payload.order_type == OrderType.MARKET:
            await self._fill(order, portfolio, market_price, is_maker=False)
        else:
            # Limit / stop / TP — queue for later processing
            order.status = OrderStatus.OPEN
            self._db.add(order)
            await self._db.flush()
            await self._db.refresh(order)
            logger.info(
                "Paper order queued",
                id=str(order.id),
                symbol=order.symbol,
                type=order.order_type,
                side=order.side,
                price=str(payload.price or payload.stop_price),
            )

        return order

    # ── Internal fill logic ───────────────────────────────────────────────────

    async def _fill(
        self,
        order: Order,
        portfolio: Portfolio,
        market_price: Decimal,
        is_maker: bool = False,
    ) -> None:
        """
        Apply slippage & fee, update position and portfolio balance, record equity.
        Mutates order and portfolio in-place; flushes to DB but does not commit.
        """
        if order.order_type == OrderType.MARKET:
            fill_price, slippage_cost = self._slip.fill_price(
                market_price, order.side.value, order.quantity
            )
        else:
            # Limit fill at the requested price — maker fee, no slippage
            fill_price = order.price or market_price
            slippage_cost = Decimal("0")
            is_maker = True

        notional = fill_price * order.quantity
        fee = calc_fee(order.exchange, notional, is_maker=is_maker)

        # Balance check (buy orders consume balance)
        if order.side == OrderSide.BUY:
            required = notional + fee
            if portfolio.available_balance < required:
                order.status = OrderStatus.REJECTED
                self._db.add(order)
                await self._db.flush()
                raise InsufficientBalanceError(
                    f"Need {required:.2f} USDT, available {portfolio.available_balance:.2f}"
                )

        # Update position
        realized_pnl = await self._update_position(
            portfolio, order.symbol, order.side, order.quantity, fill_price
        )

        # Settle order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_fill_price = fill_price
        order.fee = fee
        order.fee_currency = portfolio.quote_currency

        # Adjust free balance
        if order.side == OrderSide.BUY:
            portfolio.available_balance -= notional + fee
        else:
            portfolio.available_balance += notional - fee

        portfolio.realized_pnl += realized_pnl
        portfolio.daily_pnl += realized_pnl

        await self._refresh_totals(portfolio, fill_price, order.symbol)

        self._db.add(order)
        self._db.add(portfolio)
        await self._db.flush()
        await self._db.refresh(order)
        await self._snapshot(portfolio)

        # Trigger Trade Reflection Celery Task
        try:
            from app.workers.tasks.trading_tasks import reflect_on_completed_trade

            reflect_on_completed_trade.delay(str(order.id), float(realized_pnl))
        except Exception as e:
            logger.warning(f"Failed to trigger trade reflection task: {e}")

        logger.info(
            "Paper order filled",
            id=str(order.id),
            symbol=order.symbol,
            side=order.side,
            fill_price=str(fill_price),
            qty=str(order.quantity),
            fee=str(fee),
            slippage=str(slippage_cost),
            realized_pnl=str(realized_pnl),
        )

    # ── Position management ───────────────────────────────────────────────────

    async def _update_position(
        self,
        portfolio: Portfolio,
        symbol: str,
        order_side: OrderSide,
        quantity: Decimal,
        fill_price: Decimal,
    ) -> Decimal:
        """Open, average, or close a position. Returns realized PnL."""
        stmt = select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.symbol == symbol,
        )
        result = await self._db.execute(stmt)
        pos: Position | None = result.scalar_one_or_none()

        realized_pnl = Decimal("0")

        if pos is None:
            # Open fresh position
            new_side = PositionSide.LONG if order_side == OrderSide.BUY else PositionSide.SHORT
            pos = Position(
                portfolio_id=portfolio.id,
                symbol=symbol,
                side=new_side,
                quantity=quantity,
                entry_price=fill_price,
                current_price=fill_price,
                leverage=1,
                unrealized_pnl=Decimal("0"),
                unrealized_pnl_pct=Decimal("0"),
            )
            self._db.add(pos)
            return realized_pnl

        is_long = pos.side == PositionSide.LONG
        adding = (is_long and order_side == OrderSide.BUY) or (
            not is_long and order_side == OrderSide.SELL
        )

        if adding:
            # Average into existing position
            new_total_value = pos.entry_price * pos.quantity + fill_price * quantity
            pos.quantity += quantity
            pos.entry_price = (new_total_value / pos.quantity).quantize(Decimal("0.00000001"))
        else:
            # Reduce / close position
            close_qty = min(quantity, pos.quantity)
            if is_long:
                realized_pnl = (fill_price - pos.entry_price) * close_qty
            else:
                realized_pnl = (pos.entry_price - fill_price) * close_qty

            pos.quantity -= close_qty
            remainder = quantity - close_qty

            if pos.quantity <= _DUST:
                await self._db.delete(pos)
                pos = None
            else:
                pos.current_price = fill_price
                self._set_unrealized(pos)

            # If more quantity remains, flip to opposite position
            if remainder > _DUST:
                flip_side = PositionSide.LONG if order_side == OrderSide.BUY else PositionSide.SHORT
                flip_pos = Position(
                    portfolio_id=portfolio.id,
                    symbol=symbol,
                    side=flip_side,
                    quantity=remainder,
                    entry_price=fill_price,
                    current_price=fill_price,
                    leverage=1,
                    unrealized_pnl=Decimal("0"),
                    unrealized_pnl_pct=Decimal("0"),
                )
                self._db.add(flip_pos)

        if pos is not None:
            pos.current_price = fill_price
            self._set_unrealized(pos)

        return realized_pnl

    @staticmethod
    def _set_unrealized(pos: Position) -> None:
        if pos.side == PositionSide.LONG:
            pos.unrealized_pnl = (pos.current_price - pos.entry_price) * pos.quantity
        else:
            pos.unrealized_pnl = (pos.entry_price - pos.current_price) * pos.quantity

        if pos.entry_price > 0 and pos.quantity > 0:
            pos.unrealized_pnl_pct = pos.unrealized_pnl / (pos.entry_price * pos.quantity)
        else:
            pos.unrealized_pnl_pct = Decimal("0")

    # ── Portfolio totals ──────────────────────────────────────────────────────

    async def _refresh_totals(
        self, portfolio: Portfolio, last_price: Decimal, updated_symbol: str
    ) -> None:
        """Recompute total_value_usdt and unrealized_pnl from all live positions."""
        stmt = select(Position).where(Position.portfolio_id == portfolio.id)
        result = await self._db.execute(stmt)
        positions = list(result.scalars().all())

        total_unrealized = Decimal("0")
        positions_value = Decimal("0")
        for p in positions:
            if p.symbol == updated_symbol:
                p.current_price = last_price
                self._set_unrealized(p)
            total_unrealized += p.unrealized_pnl
            positions_value += p.current_price * p.quantity

        portfolio.unrealized_pnl = total_unrealized
        portfolio.total_value_usdt = portfolio.available_balance + positions_value

    # ── Equity snapshot ───────────────────────────────────────────────────────

    async def _snapshot(self, portfolio: Portfolio) -> None:
        point = EquityPoint(
            portfolio_id=portfolio.id,
            timestamp=datetime.now(UTC),
            equity=portfolio.total_value_usdt,
            balance=portfolio.available_balance,
            unrealized_pnl=portfolio.unrealized_pnl,
            realized_pnl=portfolio.realized_pnl,
            daily_pnl=portfolio.daily_pnl,
        )
        self._db.add(point)

    # ── Limit / stop order monitoring ─────────────────────────────────────────

    async def process_pending_orders(self, portfolio: Portfolio) -> list[Order]:
        """
        Check all OPEN limit/stop orders and fill those whose price condition is met.
        Intended to be called from the background task every ~10 seconds.
        Returns the list of newly filled orders.
        """
        open_orders = await self._order_repo.get_open_orders(portfolio.id)
        filled: list[Order] = []

        for order in open_orders:
            try:
                price = await self.get_market_price(portfolio.exchange, order.symbol)
            except ExchangeError:
                continue

            if not self._should_fill(order, price):
                continue

            # Reload portfolio with freshest positions
            fresh = await self._portfolio_repo.get_with_positions(portfolio.id)
            if fresh is None:
                continue

            try:
                await self._fill(order, fresh, price, is_maker=True)
                filled.append(order)
            except InsufficientBalanceError as e:
                logger.warning(
                    "Limit order rejected (balance)", order_id=str(order.id), error=str(e)
                )
                order.status = OrderStatus.REJECTED
                self._db.add(order)
                await self._db.flush()

        return filled

    @staticmethod
    def _should_fill(order: Order, price: Decimal) -> bool:
        """True when current market price satisfies the order's trigger condition."""
        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY and order.price:
                return price <= order.price
            if order.side == OrderSide.SELL and order.price:
                return price >= order.price

        elif order.order_type in (OrderType.STOP_LOSS, OrderType.STOP_LOSS_LIMIT):
            if order.side == OrderSide.SELL and order.stop_price:
                return price <= order.stop_price
            if order.side == OrderSide.BUY and order.stop_price:
                return price >= order.stop_price

        elif order.order_type == OrderType.TAKE_PROFIT:
            if order.side == OrderSide.SELL and order.stop_price:
                return price >= order.stop_price
            if order.side == OrderSide.BUY and order.stop_price:
                return price <= order.stop_price

        return False

    # ── Position price sync ───────────────────────────────────────────────────

    async def sync_positions(self, portfolio: Portfolio) -> None:
        """
        Refresh current_price on all positions, recompute unrealized PnL and
        total_value_usdt.  Called periodically to keep the dashboard up to date.
        """
        stmt = select(Position).where(Position.portfolio_id == portfolio.id)
        result = await self._db.execute(stmt)
        positions = list(result.scalars().all())
        if not positions:
            return

        for symbol in {p.symbol for p in positions}:
            try:
                price = await self.get_market_price(portfolio.exchange, symbol)
            except ExchangeError:
                continue
            for p in positions:
                if p.symbol == symbol:
                    p.current_price = price
                    self._set_unrealized(p)

        total_unrealized = sum((p.unrealized_pnl for p in positions), Decimal("0"))
        positions_value = sum((p.current_price * p.quantity for p in positions), Decimal("0"))
        portfolio.unrealized_pnl = total_unrealized
        portfolio.total_value_usdt = portfolio.available_balance + positions_value

        self._db.add(portfolio)
        await self._snapshot(portfolio)
        await self._db.flush()
