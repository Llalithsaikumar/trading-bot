"""IExecutionAgent — contract for order placement on the exchange."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.agents.graph.state import TradingState
from app.domain.enums.trading import TradingSignal


@runtime_checkable
class IExecutionAgent(Protocol):
    """
    Structural interface for the Execution Agent node.

    Implementations translate a risk-approved TradingSignal into an
    exchange order.  This node only runs when risk_approved=True.
    No trading logic is implemented in this phase.
    """

    async def can_execute(
        self,
        state: TradingState,
    ) -> tuple[bool, str]:
        """
        Pre-flight check before sending the order.

        Validates that the state has all required fields (signal, entry
        price, portfolio_id, sufficient balance, etc.).

        Args:
            state: TradingState after risk evaluation.

        Returns:
            Tuple of (ok: bool, reason: str).  reason is empty when ok=True.
        """
        ...

    async def execute(
        self,
        state: TradingState,
    ) -> tuple[str | None, str | None]:
        """
        Place the order on the configured exchange.

        Args:
            state: TradingState with risk_approved=True.

        Returns:
            Tuple of (order_id, error_message).
            order_id is None if execution failed; error_message is None on success.
        """
        ...

    async def signal_to_order_params(
        self,
        signal: TradingSignal,
        state: TradingState,
    ) -> dict:
        """
        Convert a TradingSignal into raw order parameters.

        Args:
            signal: The approved trading signal.
            state:  Full state for context (balance, positions, suggested prices).

        Returns:
            Dict with keys: symbol, side, order_type, quantity, price, stop_price.
        """
        ...
