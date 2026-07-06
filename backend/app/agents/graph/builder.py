"""
TradingGraphBuilder — assembles the 9-node LangGraph workflow with DI.

Usage:
    from app.agents.interfaces.base import AgentDependencies
    from app.agents.graph.builder import build_trading_graph

    deps = AgentDependencies(session=session, redis=redis, llm=llm)
    graph = build_trading_graph(deps)
    result = await graph.ainvoke(initial_state)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, StateGraph

from app.agents.graph.state import TradingState
from app.agents.interfaces.base import AgentDependencies
from app.agents.nodes.decision_node import DecisionAgent
from app.agents.nodes.execution_node import ExecutionAgent
from app.agents.nodes.market_node import MarketAgent
from app.agents.nodes.memory_node import MemoryAgent
from app.agents.nodes.news_node import NewsAgent
from app.agents.nodes.portfolio_node import PortfolioAgent
from app.agents.nodes.reflection_node import ReflectionAgent
from app.agents.nodes.risk_node import RiskAgent
from app.agents.nodes.technical_node import TechnicalAgent

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


# ---------------------------------------------------------------------------
# Conditional router
# ---------------------------------------------------------------------------


def _should_execute(state: TradingState) -> str:
    """Route to execution if risk approved, otherwise skip straight to reflection."""
    return "execution" if state.risk_approved else "reflection"


# ---------------------------------------------------------------------------
# Builder class
# ---------------------------------------------------------------------------


class TradingGraphBuilder:
    """
    Builds the compiled 9-node LangGraph workflow.

    Node order:
      memory → market → news → technical → portfolio → decision → risk
        → (conditional) execution → reflection → END
                      ↘ (risk rejected) reflection → END

    Each agent is instantiated with the same AgentDependencies so they
    share the DB session, Redis client, exchange client, and LLM.
    """

    def __init__(self, deps: AgentDependencies) -> None:
        self._deps = deps

    def build(self) -> CompiledStateGraph:
        # ── Instantiate all 9 agents with injected dependencies ───────────────
        memory_agent = MemoryAgent(self._deps)
        market_agent = MarketAgent(self._deps)
        news_agent = NewsAgent(self._deps)
        technical_agent = TechnicalAgent(self._deps)
        portfolio_agent = PortfolioAgent(self._deps)
        decision_agent = DecisionAgent(self._deps)
        risk_agent = RiskAgent(self._deps)
        execution_agent = ExecutionAgent(self._deps)
        reflection_agent = ReflectionAgent(self._deps)

        # ── Build state graph ─────────────────────────────────────────────────
        graph = StateGraph(TradingState)

        # Register nodes (bound methods are callable — LangGraph accepts them)
        graph.add_node("memory", memory_agent.run)
        graph.add_node("market", market_agent.run)
        graph.add_node("news", news_agent.run)
        graph.add_node("technical", technical_agent.run)
        graph.add_node("portfolio", portfolio_agent.run)
        graph.add_node("decision", decision_agent.run)
        graph.add_node("risk", risk_agent.run)
        graph.add_node("execution", execution_agent.run)
        graph.add_node("reflection", reflection_agent.run)

        # ── Linear edges: memory → … → risk ──────────────────────────────────
        graph.set_entry_point("memory")
        graph.add_edge("memory", "market")
        graph.add_edge("market", "news")
        graph.add_edge("news", "technical")
        graph.add_edge("technical", "portfolio")
        graph.add_edge("portfolio", "decision")
        graph.add_edge("decision", "risk")

        # ── Conditional edge: execution or skip ───────────────────────────────
        graph.add_conditional_edges(
            "risk",
            _should_execute,
            {
                "execution": "execution",
                "reflection": "reflection",
            },
        )

        # ── Terminal edges ────────────────────────────────────────────────────
        graph.add_edge("execution", "reflection")
        graph.add_edge("reflection", END)

        return graph.compile()


# ---------------------------------------------------------------------------
# Module-level factory (convenience / backwards-compat)
# ---------------------------------------------------------------------------


def build_trading_graph(
    deps: AgentDependencies | None = None,
) -> CompiledStateGraph:
    """
    Build and compile the trading graph with optional dependency injection.

    Args:
        deps: Pre-populated AgentDependencies.  If None, an empty (no-op)
              deps object is used — suitable for testing stubs.

    Returns:
        A compiled LangGraph StateGraph ready for ainvoke().
    """
    return TradingGraphBuilder(deps or AgentDependencies()).build()
