"""
Technical indicator computation helpers.
Uses pandas + ta-lib (or pandas-ta as fallback).
"""
from __future__ import annotations

from typing import Any

import pandas as pd


def ohlcv_to_dataframe(candles: list[list[Any]]) -> pd.DataFrame:
    """
    Convert CCXT OHLCV list to a typed DataFrame.
    CCXT format: [timestamp_ms, open, high, low, close, volume]
    """
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col])
    return df


try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False


def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    if HAS_TALIB:
        values = talib.RSI(df["close"].values, timeperiod=period)
        return pd.Series(values, index=df.index)
    
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).copy()
    loss = (-delta.where(delta < 0, 0)).copy()
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """MACD line, signal line, and histogram."""
    if HAS_TALIB:
        macd_line, signal_line, histogram = talib.MACD(
            df["close"].values, fastperiod=fast, slowperiod=slow, signalperiod=signal
        )
        return pd.DataFrame(
            {
                "macd": macd_line,
                "macd_signal": signal_line,
                "macd_histogram": histogram,
            },
            index=df.index,
        )

    macd_line = compute_ema(df, fast) - compute_ema(df, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame(
        {
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": histogram,
        },
        index=df.index,
    )


def compute_bollinger_bands(
    df: pd.DataFrame, period: int = 20, std_dev: float = 2.0
) -> pd.DataFrame:
    """Upper, middle (SMA), lower Bollinger Bands."""
    if HAS_TALIB:
        upper, middle, lower = talib.BBANDS(
            df["close"].values, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev, matype=0
        )
        return pd.DataFrame(
            {
                "bb_upper": upper,
                "bb_middle": middle,
                "bb_lower": lower,
            },
            index=df.index,
        )

    middle = df["close"].rolling(window=period).mean()
    std = df["close"].rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return pd.DataFrame(
        {
            "bb_upper": upper,
            "bb_middle": middle,
            "bb_lower": lower,
        },
        index=df.index,
    )


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    if HAS_TALIB:
        values = talib.ATR(
            df["high"].values, df["low"].values, df["close"].values, timeperiod=period
        )
        return pd.Series(values, index=df.index)

    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    return atr


def compute_ema(df: pd.DataFrame, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return df["close"].ewm(span=period, adjust=False).mean()


def compute_all_indicators(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute a standard indicator bundle for LLM context.
    Returns a dict suitable for JSON serialisation.
    """
    if len(df) == 0:
        return {}

    rsi = compute_rsi(df)
    macd_df = compute_macd(df)
    bb_df = compute_bollinger_bands(df)
    atr = compute_atr(df)
    ema_20 = compute_ema(df, 20)
    ema_50 = compute_ema(df, 50)

    # Return as dict of latest values
    return {
        "rsi": float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 0.0,
        "macd": float(macd_df["macd"].iloc[-1]) if not pd.isna(macd_df["macd"].iloc[-1]) else 0.0,
        "macd_signal": float(macd_df["macd_signal"].iloc[-1])
        if not pd.isna(macd_df["macd_signal"].iloc[-1])
        else 0.0,
        "macd_histogram": float(macd_df["macd_histogram"].iloc[-1])
        if not pd.isna(macd_df["macd_histogram"].iloc[-1])
        else 0.0,
        "bb_upper": float(bb_df["bb_upper"].iloc[-1]) if not pd.isna(bb_df["bb_upper"].iloc[-1]) else 0.0,
        "bb_middle": float(bb_df["bb_middle"].iloc[-1])
        if not pd.isna(bb_df["bb_middle"].iloc[-1])
        else 0.0,
        "bb_lower": float(bb_df["bb_lower"].iloc[-1]) if not pd.isna(bb_df["bb_lower"].iloc[-1]) else 0.0,
        "atr": float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0,
        "ema_20": float(ema_20.iloc[-1]) if not pd.isna(ema_20.iloc[-1]) else 0.0,
        "ema_50": float(ema_50.iloc[-1]) if not pd.isna(ema_50.iloc[-1]) else 0.0,
    }

