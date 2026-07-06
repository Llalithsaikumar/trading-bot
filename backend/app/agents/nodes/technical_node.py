"""
Technical Agent node — computes technical indicators from OHLCV data using pandas-ta.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pandas as pd
import pandas_ta as ta
from sqlalchemy import select

from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.domain.models.market_data import TechnicalIndicator
from app.domain.schemas.market_data import Analysis

if TYPE_CHECKING:
    from app.agents.graph.state import TradingState


class TechnicalAgent(BaseAgent):
    """
    Implements ITechnicalAgent.
    Graph position: fourth (after NewsAgent).
    Populates: state.indicators with structured Analysis objects.
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)

    async def run(self, state: TradingState) -> dict[str, Any]:
        if state.indicators:
            self._log_info("indicators already computed, skipping for idempotency")
            return {"indicators": state.indicators}

        self._log_info("computing indicators", symbols=list(state.ohlcv.keys()))
        try:

            indicators: dict[str, dict[str, Any]] = {}

            for symbol, ohlcv in state.ohlcv.items():
                if not ohlcv:
                    continue

                # 1. Compute indicators using pandas-ta
                analysis = self.compute_indicators_df(ohlcv)

                # Convert Pydantic model to dictionary for TradingState compatibility
                indicators[symbol] = analysis.model_dump()

                # 2. Persist to PostgreSQL
                if self._deps.session:
                    latest_candle = ohlcv[-1]
                    ts = latest_candle["timestamp"]
                    if isinstance(ts, str):
                        import arrow
                        ts_dt = arrow.get(ts).datetime
                    elif isinstance(ts, (int, float)):
                        ts_dt = datetime.fromtimestamp(ts / 1000, tz=UTC)
                    else:
                        ts_dt = ts

                    # Check if already exists to prevent duplicate key constraint
                    stmt = select(TechnicalIndicator).where(
                        TechnicalIndicator.exchange == state.exchange,
                        TechnicalIndicator.symbol == symbol,
                        TechnicalIndicator.timeframe == state.timeframe,
                        TechnicalIndicator.timestamp == ts_dt,
                    )
                    res = await self._deps.session.execute(stmt)
                    existing = res.scalar_one_or_none()

                    if existing:
                        db_ind = existing
                    else:
                        db_ind = TechnicalIndicator(
                            exchange=state.exchange,
                            symbol=symbol,
                            timeframe=state.timeframe,
                            timestamp=ts_dt,
                        )
                        self._deps.session.add(db_ind)

                    db_ind.rsi = Decimal(str(analysis.rsi))
                    db_ind.ema_20 = Decimal(str(analysis.ema_20))
                    db_ind.ema_50 = Decimal(str(analysis.ema_50))
                    db_ind.macd = Decimal(str(analysis.macd))
                    db_ind.macd_signal = Decimal(str(analysis.macd_signal))
                    db_ind.macd_histogram = Decimal(str(analysis.macd_histogram))
                    db_ind.atr = Decimal(str(analysis.atr))
                    db_ind.bb_upper = Decimal(str(analysis.bb_upper))
                    db_ind.bb_middle = Decimal(str(analysis.bb_middle))
                    db_ind.bb_lower = Decimal(str(analysis.bb_lower))
                    db_ind.vwap = (
                        Decimal(str(analysis.vwap)) if analysis.vwap is not None else None
                    )
                    db_ind.adx = Decimal(str(analysis.adx)) if analysis.adx is not None else None

                    await self._deps.session.flush()

            self._log_info("indicators computed and stored", symbols=list(indicators.keys()))
            return {"indicators": indicators}
        except Exception as exc:
            return self._node_error(state, exc)

    def compute_indicators_df(self, ohlcv: list[dict[str, Any]]) -> Analysis:
        # Convert list of dicts to pandas DataFrame
        df = pd.DataFrame(ohlcv)
        # Ensure correct column names for pandas-ta
        df.rename(
            columns={
                "timestamp": "timestamp",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
            },
            inplace=True,
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)

        # Run pandas-ta calculations
        df.ta.rsi(length=14, append=True)
        df.ta.ema(length=20, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.atr(length=14, append=True)
        df.ta.bbands(length=20, std=2.0, append=True)
        try:
            df.ta.vwap(append=True)
        except Exception:
            # VWAP fallback if calculation errors on mock data
            pass
        df.ta.adx(length=14, append=True)

        def get_col_val(prefix: str, default: float = 0.0) -> Decimal:
            cols = [c for c in df.columns if c.lower().startswith(prefix.lower())]
            if cols and not pd.isna(df[cols[0]].iloc[-1]):
                return Decimal(str(float(df[cols[0]].iloc[-1])))
            return Decimal(str(default))

        return Analysis(
            rsi=get_col_val("RSI"),
            ema_20=get_col_val("EMA_20"),
            ema_50=get_col_val("EMA_50"),
            macd=get_col_val("MACD_12"),
            macd_signal=get_col_val("MACDs"),
            macd_histogram=get_col_val("MACDh"),
            atr=get_col_val("ATR"),
            bb_upper=get_col_val("BBU"),
            bb_middle=get_col_val("BBM"),
            bb_lower=get_col_val("BBL"),
            vwap=get_col_val("VWAP")
            if any(c.lower().startswith("vwap") for c in df.columns)
            else None,
            adx=get_col_val("ADX")
            if any(c.lower().startswith("adx") for c in df.columns)
            else None,
        )
