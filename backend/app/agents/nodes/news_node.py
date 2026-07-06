"""
News Agent node — fetches news and computes market sentiment.

Aggregates recent news for the traded symbols into a MarketSentiment
object and optionally uses an LLM for nuanced sentiment scoring.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.agents.graph.state import MarketSentiment, NewsItem, TradingState
from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.agents.interfaces.news_agent import INewsAgent


class NewsAgent(BaseAgent):
    """
    Implements INewsAgent.

    Graph position: third (after MarketAgent).
    Populates: state.news_items, state.sentiment
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)

    async def run(self, state: TradingState) -> dict[str, Any]:
        self._log_info("fetching news", symbols=state.symbols)
        try:
            news_items = await self.fetch_news(state.symbols, limit=20)
            sentiment = await self.compute_sentiment(news_items, state.symbols)

            self._log_info(
                "news fetched",
                items=len(news_items),
                sentiment=sentiment.label,
                score=sentiment.overall_score,
            )
            return {"news_items": news_items, "sentiment": sentiment}
        except Exception as exc:
            return self._node_error(state, exc)

    # ── INewsAgent implementation ─────────────────────────────────────────────

    async def fetch_news(
        self,
        symbols: list[str],
        limit: int = 20,
    ) -> list[NewsItem]:
        from datetime import UTC, datetime, timedelta

        from app.agents.graph.state import NewsItem

        primary = symbols[0] if symbols else "BTC"

        mock_headlines = [
            (f"{primary} hits new weekly high amid positive regulatory signals", "CoinDesk", 0.6),
            (
                f"Quantitative analysts debate {primary} short-term resistance level",
                "Cointelegraph",
                0.1,
            ),
            (
                f"Macro headwinds trigger slight consolidation in {primary} markets",
                "Bloomberg",
                -0.2,
            ),
            (f"Institutional interest in {primary} spot products remains robust", "Reuters", 0.4),
        ]

        items = []
        now = datetime.now(UTC)
        for i, (title, source, sentiment) in enumerate(mock_headlines):
            items.append(
                NewsItem(
                    title=title,
                    source=source,
                    published_at=now - timedelta(hours=i * 2),
                    summary=f"Market snapshot showing {title}. Volume remains average as traders observe global trends.",
                    url=f"https://example.com/news/{i}",
                    sentiment_score=sentiment,
                    symbols=symbols,
                )
            )

        return items[:limit]

    async def compute_sentiment(
        self,
        news_items: list[NewsItem],
        symbols: list[str],
    ) -> MarketSentiment:
        # TODO: average item.sentiment_score weighted by recency;
        #       optionally call LLM for nuanced scoring via NEWS_SENTIMENT_SYSTEM_PROMPT
        if not news_items:
            return MarketSentiment(
                overall_score=0.0,
                label="neutral",
                items=[],
                fetched_at=datetime.now(UTC),
            )

        avg_score = sum(item.sentiment_score for item in news_items) / len(news_items)
        label = "bullish" if avg_score > 0.2 else "bearish" if avg_score < -0.2 else "neutral"
        return MarketSentiment(
            overall_score=avg_score,
            label=label,
            items=news_items,
            fetched_at=datetime.now(UTC),
        )
