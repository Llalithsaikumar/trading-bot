"""
Risk rule definitions and position sizing (Kelly Criterion & 1% Account Risk).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from decimal import Decimal
from typing import Any, Coroutine
import uuid

from sqlalchemy import select

from app.agents.graph.state import TradingState
from app.core.config import settings
from app.domain.models.portfolio import EquityPoint

RuleResult = tuple[bool, str]
RuleFn = Callable[[TradingState, Any], RuleResult | Coroutine[Any, Any, RuleResult]]


def check_neutral_signal(state: TradingState, session: Any) -> RuleResult:
    """Skip execution for NEUTRAL signals — nothing to do."""
    from app.domain.enums.trading import TradingSignal

    if state.signal == TradingSignal.NEUTRAL or state.signal is None:
        return False, "Signal is NEUTRAL — no order to execute"
    return True, ""


def check_sufficient_balance(state: TradingState, session: Any) -> RuleResult:
    """Ensure available balance is positive before attempting an order."""
    if state.available_balance <= Decimal("0"):
        return False, "Insufficient balance (available_balance ≤ 0)"
    return True, ""


def check_signal_confidence(state: TradingState, session: Any) -> RuleResult:
    """Reject signals with confidence below the minimum threshold."""
    min_confidence = 0.6
    if state.confidence < min_confidence:
        return (
            False,
            f"Confidence {state.confidence:.2f} is below threshold {min_confidence}",
        )
    return True, ""


def check_daily_loss_limit(state: TradingState, session: Any) -> RuleResult:
    """Block trading if today's realised PnL exceeds the max daily loss threshold."""
    daily_pnl = state.portfolio_metrics.daily_pnl
    total_value = state.portfolio_metrics.total_value_usdt
    if total_value <= 0:
        return True, ""
    loss_pct = float(abs(daily_pnl) / total_value) * 100
    if daily_pnl < 0 and loss_pct >= settings.MAX_DAILY_LOSS_PCT:
        return False, f"Daily loss {loss_pct:.2f}% exceeds limit {settings.MAX_DAILY_LOSS_PCT}%"
    return True, ""


def check_max_open_positions(state: TradingState, session: Any) -> RuleResult:
    """Block new orders if 5 or more positions are already open."""
    current = len(state.open_positions)
    if current >= 5:
        return False, f"Max open positions reached ({current}/5)"
    return True, ""


async def check_max_drawdown(state: TradingState, session: Any) -> RuleResult:
    """Block trading if current drawdown from peak equity is 10% or more."""
    if not session or not state.portfolio_id:
        return True, ""

    from app.infrastructure.repositories.portfolio_repository import EquityRepository

    repo = EquityRepository(session)
    equity_values = await repo.get_equity_values(uuid.UUID(state.portfolio_id))
    if not equity_values:
        return True, ""

    peak = max(equity_values)
    current = equity_values[-1]
    if peak > 0:
        drawdown = (peak - current) / peak * 100
        if drawdown >= Decimal("10.0"):
            return (
                False,
                f"Maximum drawdown limit of 10% exceeded: {drawdown:.2f}% (Peak: {peak:.2f}, Current: {current:.2f})",
            )
    return True, ""


async def check_consecutive_losses(state: TradingState, session: Any) -> RuleResult:
    """Block trading if the last 3 closed trades were consecutive losses."""
    if not session or not state.portfolio_id:
        return True, ""

    from app.infrastructure.repositories.portfolio_repository import EquityRepository

    repo = EquityRepository(session)
    trade_pnls = await repo.get_closed_trade_pnls(uuid.UUID(state.portfolio_id))
    if len(trade_pnls) >= 3 and all(pnl < 0 for pnl in trade_pnls[-3:]):
        return (
            False,
            f"Trading blocked: 3 consecutive losses detected in recent trades (Last 3: {[float(x) for x in trade_pnls[-3:]]})",
        )
    return True, ""


def check_max_leverage(state: TradingState, session: Any) -> RuleResult:
    """Block new order if it causes portfolio exposure to exceed 2x equity."""
    equity = state.portfolio_metrics.total_value_usdt
    if equity <= 0:
        return True, ""

    primary_symbol = state.symbols[0] if state.symbols else ""
    ticker = state.tickers.get(primary_symbol, {})
    last_price = Decimal(str(ticker.get("last") or 0))
    if last_price <= 0:
        last_price = Decimal("1.0")

    # If suggested size is computed, use it; otherwise estimate standard size (e.g. 5% value)
    size = state.suggested_size
    if not size or size <= 0:
        size = (equity * Decimal("0.05")) / last_price

    proposed_new_exposure = size * last_price
    current_exposure = state.portfolio_metrics.exposure
    total_exposure = current_exposure + proposed_new_exposure
    leverage = total_exposure / equity

    if leverage > Decimal("2.0"):
        return (
            False,
            f"Leverage limit of 2x exceeded: {leverage:.2f}x (Exposure: {total_exposure:.2f}, Equity: {equity:.2f})",
        )
    return True, ""


def check_position_sizing_and_kelly(state: TradingState, session: Any) -> RuleResult:
    """
    Calculates the risk-adjusted optimal position size using:
    1. Maximum 1% Account Risk per trade (Unit Risk).
    2. Kelly Criterion sizing (using win rate and risk-to-reward ratio).
    Fills state.suggested_size with the minimum of both values.
    """
    entry = state.suggested_entry
    sl = state.suggested_stop_loss
    tp = state.suggested_take_profit

    if not entry or not sl:
        return False, "Stop loss and entry price are required to calculate risk-adjusted size"

    equity = state.portfolio_metrics.total_value_usdt
    if equity <= 0:
        return False, "Total portfolio value is zero — cannot size trade"

    # 1. 1% Account Risk Sizing
    unit_risk = abs(entry - sl)
    if unit_risk <= 0:
        return False, "Invalid stop loss: unit risk is zero"

    max_loss_allowed = equity * Decimal("0.01")
    risk_size = max_loss_allowed / unit_risk

    # 2. Kelly Criterion Sizing
    win_rate = state.portfolio_metrics.win_rate
    if win_rate <= 0:
        # Default to conservative 50% win rate if no closed trades exist yet
        win_rate = 0.5

    # Win/Loss ratio r = reward / risk
    reward = abs(tp - entry) if tp else unit_risk * Decimal("2.0")  # Default to 2:1 RR if TP not set
    r = float(reward / unit_risk)
    if r <= 0:
        r = 1.0

    # Kelly formula: f* = p - (1 - p) / r
    p = win_rate
    kelly_f = p - (1 - p) / r

    # Use a conservative Half-Kelly approach to avoid over-sizing
    half_kelly_f = Decimal(str(max(0.0, 0.5 * kelly_f)))

    if half_kelly_f <= 0:
        return False, f"Kelly Criterion suggests rejecting the trade: negative expected value (win rate: {p:.2f}, RR: {r:.2f})"

    kelly_capital = half_kelly_f * equity
    kelly_size = kelly_capital / entry

    # Set suggested_size to the minimum of 1% risk size and Kelly size
    optimal_size = min(risk_size, kelly_size)
    if optimal_size <= 0:
        return False, "Calculated risk-adjusted position size is zero"

    state.suggested_size = optimal_size
    return (
        True,
        f"Position sized: {optimal_size:.4f} units (Risk limit size: {risk_size:.4f}, Kelly size: {kelly_size:.4f})",
    )


# ---------------------------------------------------------------------------
# Ordered rule list applied by RiskAgent.evaluate()
# ---------------------------------------------------------------------------
RISK_RULES: list[RuleFn] = [
    check_neutral_signal,  # Fast-exit for NEUTRAL signals
    check_sufficient_balance,  # No balance → no trade
    check_signal_confidence,  # Low confidence → no trade
    check_daily_loss_limit,  # Daily loss circuit breaker
    check_max_open_positions,  # Maximum 5 open positions limit
    check_max_drawdown,  # Maximum drawdown 10% limit
    check_consecutive_losses,  # Stop after 3 consecutive losses
    check_position_sizing_and_kelly,  # Position sizing + Kelly Criterion support
    check_max_leverage,  # Maximum leverage 2x limit (evaluates the sized trade)
]
