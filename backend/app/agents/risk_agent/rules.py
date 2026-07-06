"""
Risk rule definitions.

Each rule is a callable that receives TradingState and returns
(passed: bool, note: str).  Rules are ordered and applied sequentially
by RiskAgent.evaluate().
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from app.agents.graph.state import TradingState
from app.core.config import settings

RuleResult = tuple[bool, str]
RuleFn = Callable[[TradingState], RuleResult]


def check_neutral_signal(state: TradingState) -> RuleResult:
    """Skip execution for NEUTRAL signals — nothing to do."""
    from app.domain.enums.trading import TradingSignal

    if state.signal == TradingSignal.NEUTRAL or state.signal is None:
        return False, "Signal is NEUTRAL — no order to execute"
    return True, ""


def check_sufficient_balance(state: TradingState) -> RuleResult:
    """Ensure available balance is positive before attempting an order."""
    if state.available_balance <= Decimal("0"):
        return False, "Insufficient balance (available_balance ≤ 0)"
    return True, ""


def check_signal_confidence(state: TradingState) -> RuleResult:
    """Reject signals with confidence below the minimum threshold."""
    min_confidence = 0.6
    if state.confidence < min_confidence:
        return (
            False,
            f"Confidence {state.confidence:.2f} is below threshold {min_confidence}",
        )
    return True, ""


def check_daily_loss_limit(state: TradingState) -> RuleResult:
    """Block trading if today's realised PnL exceeds the max daily loss threshold."""
    daily_pnl = state.portfolio_metrics.daily_pnl
    total_value = state.portfolio_metrics.total_value_usdt
    if total_value <= 0:
        return True, ""  # Can't evaluate without portfolio value
    loss_pct = float(abs(daily_pnl) / total_value) * 100
    if daily_pnl < 0 and loss_pct >= settings.MAX_DAILY_LOSS_PCT:
        return False, f"Daily loss {loss_pct:.2f}% exceeds limit {settings.MAX_DAILY_LOSS_PCT}%"
    return True, ""


def check_max_open_positions(state: TradingState) -> RuleResult:
    """Block new orders if the max concurrent open positions is reached."""
    max_positions = 3  # TODO: load from strategy config
    current = len(state.open_positions)
    if current >= max_positions:
        return False, f"Max open positions reached ({current}/{max_positions})"
    return True, ""


def check_position_size(state: TradingState) -> RuleResult:
    """Ensure the proposed order does not exceed max position size."""
    # TODO: compute proposed order value vs portfolio total value
    return True, ""


# ---------------------------------------------------------------------------
# Ordered rule list applied by RiskAgent.evaluate()
# ---------------------------------------------------------------------------
RISK_RULES: list[RuleFn] = [
    check_neutral_signal,  # Fast-exit for NEUTRAL signals
    check_sufficient_balance,  # No balance → no trade
    check_signal_confidence,  # Low confidence → no trade
    check_daily_loss_limit,  # Daily loss circuit breaker
    check_max_open_positions,  # Concurrency limit
    check_position_size,  # Size validation (TODO: full impl)
]
