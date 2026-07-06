"""
Technical Agent node — computes technical indicators from OHLCV data.

Reuses the indicator helpers in app/agents/analysis_agent/indicators.py
and wraps them in the modular node interface.
"""

from __future__ import annotations

from typing import Any

from app.agents.analysis_agent.indicators import compute_all_indicators, ohlcv_to_dataframe
from app.agents.graph.state import TradingState
from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.agents.interfaces.technical_agent import ITechnicalAgent


class TechnicalAgent(BaseAgent):
    """
    Implements ITechnicalAgent.

    Graph position: fourth (after NewsAgent).
    Populates: state.indicators

    Delegates low-level computation to the indicator utility functions
    in analysis_agent/indicators.py.
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)

    async def run(self, state: TradingState) -> dict[str, Any]:
        self._log_info("computing indicators", symbols=list(state.ohlcv.keys()))
        try:
            indicators = await self.compute_all(state.ohlcv)
            self._log_info(
                "indicators computed",
                symbols=list(indicators.keys()),
            )
            return {"indicators": indicators}
        except Exception as exc:
            return self._node_error(state, exc)

    # ── ITechnicalAgent implementation ────────────────────────────────────────

    async def compute_indicators(
        self,
        symbol: str,
        ohlcv: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not ohlcv:
            return {}
        # Convert list-of-dicts to CCXT list format expected by the helpers
        ccxt_format = [
            [
                c.get("timestamp", 0),
                c.get("open", 0),
                c.get("high", 0),
                c.get("low", 0),
                c.get("close", 0),
                c.get("volume", 0),
            ]
            for c in ohlcv
        ]
        df = ohlcv_to_dataframe(ccxt_format)
        return compute_all_indicators(df)

    async def compute_all(
        self,
        ohlcv_by_symbol: dict[str, list[dict[str, Any]]],
    ) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        for symbol, ohlcv in ohlcv_by_symbol.items():
            results[symbol] = await self.compute_indicators(symbol, ohlcv)
        return results
