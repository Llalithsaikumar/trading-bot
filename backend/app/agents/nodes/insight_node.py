"""
Insight Agent node — fetches prediction markets and computes signals.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.agents.graph.state import PredictionInsight, PredictionMarketSentiment, TradingState
from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.services.polymarket.polymarket_service import PolymarketService


class InsightAgent(BaseAgent):
    """
    Implements IInsightAgent.
    Graph position: fifth (after TechnicalAgent, before PortfolioAgent).
    Populates: state.prediction_insights, state.prediction_sentiment
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)

    async def run(self, state: TradingState) -> dict[str, Any]:
        # Idempotency check
        if state.prediction_insights or (
            state.prediction_sentiment and state.prediction_sentiment.insights
        ):
            self._log_info("prediction insights already fetched, skipping for idempotency")
            return {
                "prediction_insights": state.prediction_insights,
                "prediction_sentiment": state.prediction_sentiment,
            }

        self._log_info("fetching prediction insights", symbols=state.symbols)
        try:
            insights = await self.fetch_prediction_markets(state.symbols)
            sentiment = await self.compute_market_signal(insights)

            self._log_info(
                "prediction insights fetched",
                count=len(insights),
                signal_strength=sentiment.signal_strength,
                avg_probability=sentiment.avg_probability,
            )

            return {"prediction_insights": insights, "prediction_sentiment": sentiment}
        except Exception as exc:
            return self._node_error(state, exc)

    async def fetch_prediction_markets(
        self,
        symbols: list[str],
        limit: int = 20,
    ) -> list[PredictionInsight]:
        """Fetch active prediction markets related to crypto."""
        if self._deps.session:
            service = PolymarketService(self._deps.session)
            markets = await service.fetch_crypto_markets(limit=limit)
            return [
                PredictionInsight(
                    market_id=m.condition_id,
                    question=m.question,
                    probability=m.probability,
                    liquidity=m.liquidity,
                    volume=m.volume,
                    end_date=m.end_date,
                )
                for m in markets
            ]

        self._log_warning("No DB session in dependencies, returning empty insights list")
        return []

    async def compute_market_signal(
        self,
        insights: list[PredictionInsight],
    ) -> PredictionMarketSentiment:
        """Compute aggregated prediction market sentiment signal."""
        if not insights:
            return PredictionMarketSentiment(
                bullish_count=0,
                bearish_count=0,
                avg_probability=0.5,
                total_liquidity=Decimal("0"),
                signal_strength=0.0,
                insights=[],
                fetched_at=datetime.now(UTC),
            )

        bullish_count = 0
        bearish_count = 0
        total_probability = 0.0
        total_liquidity = Decimal("0")

        for insight in insights:
            total_probability += insight.probability
            total_liquidity += insight.liquidity
            if insight.probability > 0.55:
                bullish_count += 1
            elif insight.probability < 0.45:
                bearish_count += 1

        avg_probability = total_probability / len(insights)
        
        total_active_markets = bullish_count + bearish_count
        if total_active_markets > 0:
            signal_strength = (bullish_count - bearish_count) / total_active_markets
        else:
            signal_strength = 0.0

        return PredictionMarketSentiment(
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            avg_probability=avg_probability,
            total_liquidity=total_liquidity,
            signal_strength=signal_strength,
            insights=insights,
            fetched_at=datetime.now(UTC),
        )
