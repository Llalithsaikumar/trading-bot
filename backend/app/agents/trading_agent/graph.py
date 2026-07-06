"""
Trading agent graph — backwards-compatibility shim.

The full 9-node workflow is now assembled by TradingGraphBuilder in
app/agents/graph/builder.py.  This module re-exports the compiled
graph and factory function under their original names so existing
imports (workers, tests) continue to work without changes.
"""

from __future__ import annotations

from app.agents.graph.builder import TradingGraphBuilder, build_trading_graph
from app.agents.graph.state import TradingState

# Module-level compiled graph — same contract as before
trading_graph = build_trading_graph()

__all__ = ["trading_graph", "build_trading_graph", "TradingGraphBuilder", "TradingState"]
