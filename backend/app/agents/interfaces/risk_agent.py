"""IRiskAgent — contract for validating trading signals against risk rules."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.agents.graph.state import RiskViolation, TradingState


@runtime_checkable
class IRiskAgent(Protocol):
    """
    Structural interface for the Risk Agent node.

    Implementations run an ordered set of risk rules against the current
    TradingState and return a list of any violations found.  The node
    sets risk_approved=True only when all rules pass.
    """

    async def evaluate(
        self,
        state: TradingState,
    ) -> list[RiskViolation]:
        """
        Run all configured risk rules and collect violations.

        Args:
            state: Full TradingState with decision output populated.

        Returns:
            List of RiskViolation objects.  Empty list → all rules passed.
        """
        ...

    async def compute_risk_score(
        self,
        violations: list[RiskViolation],
    ) -> float:
        """
        Compute a scalar risk score from [0.0, 1.0].

        1.0 = no risk / fully approved.
        0.0 = high risk / blocked.

        Args:
            violations: Output of evaluate().

        Returns:
            Float in [0.0, 1.0].
        """
        ...
