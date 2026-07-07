"""
LangGraph state definitions for the 9-agent trading workflow.

Sub-models are Pydantic BaseModels that live inside TradingState.
Each agent owns a specific slice of the state and returns a partial
update dict that LangGraph merges back.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Any

from langgraph.graph import add_messages
from pydantic import BaseModel, Field

from datetime import datetime
from app.domain.enums.trading import TradingSignal


# ---------------------------------------------------------------------------
# Sub-models (one per agent's output slice)
# ---------------------------------------------------------------------------


class MemoryContext(BaseModel):
    """Historical context loaded by the Memory Agent at graph start."""

    context_key: str = ""
    past_signals: list[dict[str, Any]] = Field(default_factory=list)
    past_reflections: list[dict[str, Any]] = Field(default_factory=list)
    market_patterns: list[dict[str, Any]] = Field(default_factory=list)
    relevant_news: list[dict[str, Any]] = Field(default_factory=list)
    last_updated: datetime | None = None


class NewsItem(BaseModel):
    """A single news article or market event."""

    title: str
    source: str
    published_at: datetime
    summary: str
    url: str = ""
    sentiment_score: float = 0.0  # -1.0 (bearish) to 1.0 (bullish)
    symbols: list[str] = Field(default_factory=list)


class MarketSentiment(BaseModel):
    """Aggregated sentiment from the News Agent."""

    overall_score: float = 0.0  # -1.0 to 1.0
    label: str = "neutral"  # bearish | neutral | bullish
    items: list[NewsItem] = Field(default_factory=list)
    fetched_at: datetime | None = None


class PortfolioMetrics(BaseModel):
    """Portfolio performance snapshot from the Portfolio Agent."""

    total_value_usdt: Decimal = Decimal("0")
    daily_pnl: Decimal = Decimal("0")
    daily_pnl_pct: float = 0.0
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    total_pnl: Decimal = Decimal("0")
    exposure: Decimal = Decimal("0")
    available_margin: Decimal = Decimal("0")
    open_orders: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    sharpe_ratio: float | None = None



class RiskViolation(BaseModel):
    """A single violated risk rule."""

    rule: str
    message: str
    severity: str = "error"  # warning | error | critical


class ReflectionResult(BaseModel):
    """Post-cycle analysis produced by the Reflection Agent."""

    summary: str = ""
    lessons_learned: list[str] = Field(default_factory=list)
    signal_quality_score: float = 0.0  # 0.0–1.0
    process_quality_score: float = 0.0  # 0.0–1.0
    data_quality_issues: list[str] = Field(default_factory=list)
    memory_updates: list[dict[str, Any]] = Field(default_factory=list)
    recommended_adjustments: list[str] = Field(default_factory=list)



class PredictionInsight(BaseModel):
    """A single Polymarket prediction market insight."""

    market_id: str
    question: str
    probability: float  # 0.0-1.0
    liquidity: Decimal
    volume: Decimal
    end_date: datetime | None = None


class PredictionMarketSentiment(BaseModel):
    """Aggregated prediction market signal."""

    bullish_count: int = 0
    bearish_count: int = 0
    avg_probability: float = 0.0
    total_liquidity: Decimal = Decimal("0")
    signal_strength: float = 0.0  # -1.0 to 1.0
    insights: list[PredictionInsight] = Field(default_factory=list)
    fetched_at: datetime | None = None


# ---------------------------------------------------------------------------
# Primary graph state
# ---------------------------------------------------------------------------


class TradingState(BaseModel):
    """
    Shared state passed through all 9 nodes of the trading agent graph.

    LangGraph serialises / deserialises this at each node boundary.
    Nodes return a partial dict; LangGraph merges it via model_copy(update=…).
    Fields annotated with reducers (e.g. add_messages) are handled specially.
    """

    # ── Run metadata ─────────────────────────────────────────────────────────
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    exchange: str
    symbols: list[str]
    timeframe: str

    # ── Memory Agent output ───────────────────────────────────────────────────
    memory_context: MemoryContext = Field(default_factory=MemoryContext)

    # ── Market Agent output ───────────────────────────────────────────────────
    # symbol → list of OHLCV dicts [{timestamp, open, high, low, close, volume}]
    ohlcv: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    # symbol → ticker dict {bid, ask, last, volume_24h, change_24h_pct, …}
    tickers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # symbol → order book {bids: [[price, qty], …], asks: […]}
    order_book: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # ── News Agent output ─────────────────────────────────────────────────────
    news_items: list[NewsItem] = Field(default_factory=list)
    sentiment: MarketSentiment = Field(default_factory=MarketSentiment)

    # ── Technical Agent output ────────────────────────────────────────────────
    # symbol → {rsi: …, macd: …, bb: …, ema_20: …, ema_50: …, atr: …}
    indicators: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # ── Portfolio Agent output ────────────────────────────────────────────────
    portfolio_id: str | None = None
    available_balance: Decimal = Decimal("0")
    open_positions: list[dict[str, Any]] = Field(default_factory=list)
    portfolio_metrics: PortfolioMetrics = Field(default_factory=PortfolioMetrics)

    # ── Decision Agent output ─────────────────────────────────────────────────
    signal: TradingSignal | None = None
    confidence: float = 0.0  # 0.0–1.0
    reasoning: str = ""
    analysis: str = ""  # extended market analysis narrative
    suggested_entry: Decimal | None = None
    suggested_stop_loss: Decimal | None = None
    suggested_take_profit: Decimal | None = None
    suggested_size: Decimal | None = None


    # ── Risk Agent output ─────────────────────────────────────────────────────
    risk_approved: bool = False
    risk_violations: list[RiskViolation] = Field(default_factory=list)
    risk_score: float = 1.0  # 1.0 = no risk, 0.0 = blocked

    # ── Execution Agent output ────────────────────────────────────────────────
    order_placed: bool = False
    order_id: str | None = None
    execution_error: str | None = None

    # ── Reflection Agent output ───────────────────────────────────────────────
    reflection: ReflectionResult = Field(default_factory=ReflectionResult)

    # ── Insight Agent output (Polymarket) ─────────────────────────────────────
    prediction_insights: list[PredictionInsight] = Field(default_factory=list)
    prediction_sentiment: PredictionMarketSentiment = Field(default_factory=PredictionMarketSentiment)

    # ── Diagnostics ───────────────────────────────────────────────────────────
    # Keyed by node name; set by nodes on failure
    node_errors: dict[str, str] = Field(default_factory=dict)

    # LangGraph message accumulator (for multi-turn LLM conversations)
    messages: Annotated[list[Any], add_messages] = Field(default_factory=list)
