"""
Slippage models for paper trading.

Market orders experience price impact; limit orders do not.

FIXED model: constant basis-point slippage regardless of order size.
VOLUME_IMPACT model: slippage increases as order size grows relative to daily volume.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

_DEFAULT_BPS: Decimal = Decimal("10")  # 0.10 % default slippage
_MAX_IMPACT_BPS: Decimal = Decimal("50")  # 0.50 % hard cap


class SlippageModel(StrEnum):
    FIXED = "fixed"
    VOLUME_IMPACT = "volume_impact"


class SlippageCalculator:
    def __init__(
        self,
        model: SlippageModel = SlippageModel.FIXED,
        bps: Decimal = _DEFAULT_BPS,
    ) -> None:
        self.model = model
        self.bps = bps

    def fill_price(
        self,
        mid_price: Decimal,
        side: str,
        quantity: Decimal,
        volume_24h: Decimal | None = None,
    ) -> tuple[Decimal, Decimal]:
        """
        Return (fill_price, slippage_cost_usdt).
        side: 'buy' or 'sell'
        """
        if self.model == SlippageModel.VOLUME_IMPACT and volume_24h and volume_24h > 0:
            order_notional = mid_price * quantity
            # Each % of daily volume adds 10 bps of slippage, capped at MAX_IMPACT_BPS
            pct_of_volume = order_notional / (volume_24h * Decimal("0.01"))
            effective_bps = min(self.bps + pct_of_volume * Decimal("10"), _MAX_IMPACT_BPS)
        else:
            effective_bps = self.bps

        slippage_pct = effective_bps / Decimal("10000")

        fill = mid_price * (1 + slippage_pct) if side == "buy" else mid_price * (1 - slippage_pct)

        fill = fill.quantize(Decimal("0.00000001"))
        cost = (abs(fill - mid_price) * quantity).quantize(Decimal("0.00000001"))
        return fill, cost
