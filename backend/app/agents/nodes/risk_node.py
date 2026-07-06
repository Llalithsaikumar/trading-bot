"""
Risk Agent node — validates trading signals against configured risk rules.

Reuses the functional risk rule definitions from
app/agents/risk_agent/rules.py and adds the structured RiskViolation
output and risk_score computation.
"""

from __future__ import annotations

from typing import Any

from app.agents.graph.state import RiskViolation, TradingState
from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.agents.interfaces.risk_agent import IRiskAgent
from app.agents.risk_agent.rules import RISK_RULES


class RiskAgent(BaseAgent):
    """
    Implements IRiskAgent.

    Graph position: seventh (after DecisionAgent).
    Populates: state.risk_approved, state.risk_violations, state.risk_score

    Uses the ordered RISK_RULES list from risk_agent/rules.py.
    Short-circuits on the first critical violation.
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)

    async def run(self, state: TradingState) -> dict[str, Any]:
        self._log_info("evaluating risk rules", signal=str(state.signal))
        try:
            violations = await self.evaluate(state)
            risk_score = await self.compute_risk_score(violations)
            approved = len(violations) == 0

            if approved:
                self._log_info("risk approved", score=risk_score)
            else:
                self._log_warning(
                    "risk rejected",
                    violations=[v.rule for v in violations],
                    score=risk_score,
                )

            return {
                "risk_approved": approved,
                "risk_violations": violations,
                "risk_score": risk_score,
            }
        except Exception as exc:
            return {
                **self._node_error(state, exc),
                "risk_approved": False,
                "risk_violations": [
                    RiskViolation(
                        rule="internal_error",
                        message=f"Risk agent exception: {exc}",
                        severity="critical",
                    )
                ],
                "risk_score": 0.0,
            }

    # ── IRiskAgent implementation ─────────────────────────────────────────────

    async def evaluate(self, state: TradingState) -> list[RiskViolation]:
        violations: list[RiskViolation] = []
        for rule_fn in RISK_RULES:
            passed, note = rule_fn(state)
            if not passed:
                violations.append(
                    RiskViolation(
                        rule=rule_fn.__name__,
                        message=note or f"Rule '{rule_fn.__name__}' failed",
                        severity="error",
                    )
                )
        return violations

    async def compute_risk_score(self, violations: list[RiskViolation]) -> float:
        if not violations:
            return 1.0
        # Each violation reduces the score; critical ones have double weight
        penalty = sum(0.4 if v.severity == "critical" else 0.2 for v in violations)
        return max(0.0, 1.0 - penalty)
