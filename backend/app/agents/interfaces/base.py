"""
BaseAgent abstract class and AgentDependencies injection container.

All concrete agent nodes inherit from BaseAgent and receive their
dependencies through AgentDependencies — they never import infrastructure
singletons directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.core.config import settings as _settings


@dataclass
class AgentDependencies:
    """
    Dependency injection container for all agent nodes.

    Pass an instance of this to TradingGraphBuilder.build() so every
    node receives the same shared resources without importing singletons.
    """

    # Async SQLAlchemy session (injected per graph run)
    session: Any | None = None  # AsyncSession — typed as Any to avoid circular import

    # Shared Redis client
    redis: Any | None = None  # redis.asyncio.Redis

    # CCXT exchange wrapper (ExchangeClient from infrastructure layer)
    exchange: Any | None = None

    # LangChain chat model (ChatAnthropic, ChatOpenAI, …)
    llm: Any | None = None

    # Application settings (defaults to module-level singleton)
    settings: Any = field(default_factory=lambda: _settings)


class BaseAgent(ABC):
    """
    Abstract base for every agent node in the trading workflow.

    Subclasses must implement `run(state) -> dict`, which receives the
    current TradingState and returns a *partial* dict of state updates.
    LangGraph merges the returned dict back into the state after each node.
    """

    def __init__(self, deps: AgentDependencies) -> None:
        self._deps = deps

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    async def run(self, state: Any) -> dict[str, Any]:
        """
        Execute the agent's logic and return a partial state update.

        Args:
            state: Current TradingState snapshot.

        Returns:
            Dict of field names → new values to merge into TradingState.
        """

    def _log_info(self, msg: str, **kw: Any) -> None:
        logger.info(f"[{self.name}] {msg}", **kw)

    def _log_warning(self, msg: str, **kw: Any) -> None:
        logger.warning(f"[{self.name}] {msg}", **kw)

    def _log_error(self, msg: str, **kw: Any) -> None:
        logger.error(f"[{self.name}] {msg}", **kw)

    def _node_error(self, state: Any, exc: Exception) -> dict[str, Any]:
        """Convenience: build a node_errors update without crashing the graph."""
        msg = f"{type(exc).__name__}: {exc}"
        self._log_error("unhandled exception", error=msg)
        errors = dict(state.node_errors)
        errors[self.name] = msg
        return {"node_errors": errors}
