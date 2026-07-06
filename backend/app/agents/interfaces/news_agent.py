"""INewsAgent — contract for fetching news and computing market sentiment."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.agents.graph.state import MarketSentiment, NewsItem


@runtime_checkable
class INewsAgent(Protocol):
    """
    Structural interface for the News Agent node.

    Implementations fetch recent news/events for a set of symbols and
    aggregate them into a single MarketSentiment score used by the
    Decision Agent's LLM context.
    """

    async def fetch_news(
        self,
        symbols: list[str],
        limit: int = 20,
    ) -> list[NewsItem]:
        """
        Fetch recent news items relevant to the given symbols.

        Args:
            symbols: Trading pairs to filter news for (e.g. ["BTC/USDT"]).
            limit:   Maximum number of items to return.

        Returns:
            List of NewsItem objects, newest first.
        """
        ...

    async def compute_sentiment(
        self,
        news_items: list[NewsItem],
        symbols: list[str],
    ) -> MarketSentiment:
        """
        Aggregate news items into an overall sentiment score.

        Args:
            news_items: Items returned by fetch_news().
            symbols:    Symbols to compute per-asset sentiment for.

        Returns:
            MarketSentiment with overall_score in [-1.0, 1.0] and label.
        """
        ...
