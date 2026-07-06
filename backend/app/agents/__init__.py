"""
LangGraph agent definitions for the trading platform.

Public API:
  build_trading_graph(deps)  — build the compiled 9-node workflow
  TradingGraphBuilder         — class-based builder for the workflow
  TradingState                — typed state shared by all nodes
  AgentDependencies           — DI container for all agents
  BaseAgent                   — abstract base for all agent nodes
"""

from app.agents.graph.builder import TradingGraphBuilder, build_trading_graph
from app.agents.graph.state import TradingState
from app.agents.interfaces.base import AgentDependencies, BaseAgent

__all__ = [
    "build_trading_graph",
    "TradingGraphBuilder",
    "TradingState",
    "AgentDependencies",
    "BaseAgent",
]
