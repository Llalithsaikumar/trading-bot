"""Agent interface protocols and base classes."""

from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.agents.interfaces.decision_agent import IDecisionAgent
from app.agents.interfaces.execution_agent import IExecutionAgent
from app.agents.interfaces.insight_agent import IInsightAgent
from app.agents.interfaces.market_agent import IMarketAgent
from app.agents.interfaces.memory_agent import IMemoryAgent
from app.agents.interfaces.news_agent import INewsAgent
from app.agents.interfaces.portfolio_agent import IPortfolioAgent
from app.agents.interfaces.reflection_agent import IReflectionAgent
from app.agents.interfaces.risk_agent import IRiskAgent
from app.agents.interfaces.technical_agent import ITechnicalAgent

__all__ = [
    "AgentDependencies",
    "BaseAgent",
    "IDecisionAgent",
    "IExecutionAgent",
    "IInsightAgent",
    "IMarketAgent",
    "IMemoryAgent",
    "INewsAgent",
    "IPortfolioAgent",
    "IReflectionAgent",
    "IRiskAgent",
    "ITechnicalAgent",
]
