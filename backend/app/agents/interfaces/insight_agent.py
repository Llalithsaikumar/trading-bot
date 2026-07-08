"""IInsightAgent — contract for fetching prediction markets and computing signals."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.agents.graph.state import PredictionInsight, PredictionMarketSentiment


@runtime_checkable
class IInsightAgent(Protocol):
    """
    Structural interface for the Insight Agent node.

    Implementations fetch recent crypto prediction markets from Polymarket
    and aggregate them into a PredictionMarketSentiment score.
    """

    async def fetch_prediction_markets(
        self,
        symbols: list[str],
        limit: int = 20,
    ) -> list[PredictionInsight]:
        """
        Fetch active crypto-related prediction markets.

        Args:
            symbols: Trading pairs to filter for.
            limit:   Maximum number of items to return.

        Returns:
            List of PredictionInsight objects.
        """
        ...

    async def compute_market_signal(
        self,
        insights: list[PredictionInsight],
    ) -> PredictionMarketSentiment:
        """
        Aggregate prediction markets into an overall market sentiment.

        Args:
            insights: Prediction insights returned by fetch_prediction_markets().

        Returns:
            PredictionMarketSentiment with aggregated stats.
        """
        ...
