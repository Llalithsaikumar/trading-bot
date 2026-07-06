"""
Fee schedules for each supported exchange.
Rates are based on standard (non-VIP) taker/maker tiers.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FeeSchedule:
    maker: Decimal
    taker: Decimal


# Standard retail fee rates (as decimals, not percentages)
EXCHANGE_FEES: dict[str, FeeSchedule] = {
    "binance":     FeeSchedule(maker=Decimal("0.001"),   taker=Decimal("0.001")),
    "bybit":       FeeSchedule(maker=Decimal("0.0002"),  taker=Decimal("0.00055")),
    "okx":         FeeSchedule(maker=Decimal("0.0002"),  taker=Decimal("0.0005")),
    "hyperliquid": FeeSchedule(maker=Decimal("0.0002"),  taker=Decimal("0.0005")),
}
_DEFAULT = FeeSchedule(maker=Decimal("0.001"), taker=Decimal("0.001"))


def get_schedule(exchange: str) -> FeeSchedule:
    return EXCHANGE_FEES.get(exchange.lower(), _DEFAULT)


def calc_fee(exchange: str, notional: Decimal, is_maker: bool = False) -> Decimal:
    """Return the fee for a trade of the given notional value."""
    schedule = get_schedule(exchange)
    rate = schedule.maker if is_maker else schedule.taker
    return (notional * rate).quantize(Decimal("0.00000001"))
