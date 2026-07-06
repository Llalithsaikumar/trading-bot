"""
Risk metric computation for paper trading portfolios.

All inputs and outputs use Python Decimal for precision.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

# Risk-free rate: ~5 % annual, expressed as daily return
_RISK_FREE_DAILY = Decimal("0.000198")  # 5% / 252 trading days
_SQRT_252 = Decimal(str(math.sqrt(252)))
_ZERO = Decimal("0")


@dataclass
class RiskMetrics:
    # Trade stats
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal  # 0–1
    profit_factor: Decimal  # gross_profit / gross_loss
    avg_win: Decimal  # average winning trade PnL in USDT
    avg_loss: Decimal  # average losing trade PnL in USDT (positive)
    # Drawdown
    max_drawdown: Decimal  # in USDT
    max_drawdown_pct: Decimal  # 0–1
    # Return
    total_return: Decimal  # in USDT
    total_return_pct: Decimal  # 0–1
    # Risk-adjusted returns
    sharpe_ratio: Decimal | None
    sortino_ratio: Decimal | None
    calmar_ratio: Decimal | None
    # Other
    total_fees_paid: Decimal
    var_95: Decimal  # 95 % VaR in USDT (daily)
    peak_equity: Decimal
    current_equity: Decimal


def compute(
    *,
    equity_history: list[Decimal],
    initial_equity: Decimal,
    current_equity: Decimal,
    trade_pnls: list[Decimal],
    total_fees: Decimal,
) -> RiskMetrics:
    """Compute all risk metrics from equity history and closed-trade PnLs."""

    wins = [p for p in trade_pnls if p > _ZERO]
    losses = [p for p in trade_pnls if p < _ZERO]

    win_rate = Decimal(len(wins)) / Decimal(max(len(trade_pnls), 1))
    gross_profit = sum(wins, _ZERO)
    gross_loss = abs(sum(losses, _ZERO))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else _ZERO
    avg_win = (sum(wins, _ZERO) / len(wins)) if wins else _ZERO
    avg_loss = (abs(sum(losses, _ZERO)) / len(losses)) if losses else _ZERO

    # ── Drawdown ──────────────────────────────────────────────────────────────
    max_dd = _ZERO
    max_dd_pct = _ZERO
    peak = initial_equity
    for eq in equity_history:
        if eq > peak:
            peak = eq
        dd = peak - eq
        dd_pct = (dd / peak) if peak > _ZERO else _ZERO
        if dd > max_dd:
            max_dd = dd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

    # ── Daily returns ─────────────────────────────────────────────────────────
    daily_returns: list[Decimal] = []
    if len(equity_history) >= 2:
        daily_returns = [
            (equity_history[i] - equity_history[i - 1]) / equity_history[i - 1]
            for i in range(1, len(equity_history))
            if equity_history[i - 1] > _ZERO
        ]

    sharpe = sortino = calmar = None
    if len(daily_returns) >= 2:
        n = len(daily_returns)
        mean_r = sum(daily_returns, _ZERO) / n
        excess = mean_r - _RISK_FREE_DAILY

        variance = sum((r - mean_r) ** 2 for r in daily_returns) / n
        std_r = Decimal(str(math.sqrt(float(variance)))) if variance > 0 else None
        if std_r and std_r > 0:
            sharpe = (excess / std_r * _SQRT_252).quantize(Decimal("0.001"))

        downside = [(r - _RISK_FREE_DAILY) ** 2 for r in daily_returns if r < _RISK_FREE_DAILY]
        if downside:
            down_std = Decimal(str(math.sqrt(float(sum(downside) / len(downside)))))
            if down_std > 0:
                sortino = (excess / down_std * _SQRT_252).quantize(Decimal("0.001"))

    # Calmar = annualised return / max drawdown
    if len(equity_history) >= 1 and max_dd_pct > 0 and initial_equity > 0:
        days = max(len(equity_history), 1)
        annual_ret = (current_equity - initial_equity) / initial_equity * Decimal("252") / days
        calmar = (annual_ret / max_dd_pct).quantize(Decimal("0.001"))

    # ── Total return ──────────────────────────────────────────────────────────
    total_return = current_equity - initial_equity
    total_return_pct = (total_return / initial_equity) if initial_equity > 0 else _ZERO

    # ── VaR 95 % ──────────────────────────────────────────────────────────────
    var_95 = _ZERO
    if len(daily_returns) >= 20:
        sorted_r = sorted(daily_returns)
        idx = max(int(len(sorted_r) * 0.05) - 1, 0)
        var_95 = abs(sorted_r[idx]) * current_equity

    def q(v: Decimal, places: str = "0.0001") -> Decimal:
        return v.quantize(Decimal(places))

    return RiskMetrics(
        total_trades=len(trade_pnls),
        winning_trades=len(wins),
        losing_trades=len(losses),
        win_rate=q(win_rate),
        profit_factor=q(profit_factor, "0.001"),
        avg_win=q(avg_win, "0.01"),
        avg_loss=q(avg_loss, "0.01"),
        max_drawdown=q(max_dd, "0.01"),
        max_drawdown_pct=q(max_dd_pct),
        total_return=q(total_return, "0.01"),
        total_return_pct=q(total_return_pct),
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        total_fees_paid=q(total_fees, "0.01"),
        var_95=q(var_95, "0.01"),
        peak_equity=q(peak, "0.01"),
        current_equity=q(current_equity, "0.01"),
    )
