"""IReflectionAgent — contract for post-cycle analysis and self-improvement."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.agents.graph.state import ReflectionResult, TradingState


@runtime_checkable
class IReflectionAgent(Protocol):
    """
    Structural interface for the Reflection Agent node.

    The Reflection Agent is the final node in the trading workflow.
    It reviews the entire cycle — market conditions, technical signals,
    the LLM's decision, risk evaluation outcome, and execution result —
    and produces a structured ReflectionResult that is saved to memory.

    This creates a closed feedback loop: each run informs future runs
    via MemoryContext.past_reflections.
    """

    async def reflect(
        self,
        state: TradingState,
    ) -> ReflectionResult:
        """
        Analyse the completed cycle and produce a reflection.

        Args:
            state: Final TradingState after all nodes have run.

        Returns:
            ReflectionResult with summary, lessons_learned, quality scores,
            and memory_updates to be persisted by the Memory Agent.
        """
        ...

    async def build_reflection_prompt(
        self,
        state: TradingState,
    ) -> str:
        """
        Construct the LLM prompt for the reflection step.

        The prompt includes: the original signal, risk outcome, execution
        result (or skip reason), and any node errors that occurred.

        Args:
            state: Completed TradingState.

        Returns:
            Formatted prompt string.
        """
        ...

    async def score_signal_quality(
        self,
        state: TradingState,
    ) -> float:
        """
        Score the quality of the generated trading signal [0.0, 1.0].

        Considers: confidence level, data completeness, indicator agreement,
        and alignment with historical patterns.

        Args:
            state: Completed TradingState.

        Returns:
            Float in [0.0, 1.0].
        """
        ...
