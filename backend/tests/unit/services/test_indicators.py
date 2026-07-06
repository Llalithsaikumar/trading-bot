import pandas as pd

from app.agents.analysis_agent.indicators import (
    compute_all_indicators,
    compute_atr,
    compute_bollinger_bands,
    compute_macd,
    compute_rsi,
)


def test_compute_indicators():
    # Construct mock pandas Series/DataFrame
    data = {
        "open": [100.0 + i for i in range(30)],
        "high": [102.0 + i for i in range(30)],
        "low": [98.0 + i for i in range(30)],
        "close": [101.0 + i for i in range(30)],
        "volume": [1000.0 for _ in range(30)],
    }
    df = pd.DataFrame(data)

    # Test individual functions
    rsi = compute_rsi(df, period=14)
    assert isinstance(rsi, pd.Series)
    assert len(rsi) == 30

    macd_df = compute_macd(df)
    assert isinstance(macd_df, pd.DataFrame)
    assert "macd" in macd_df
    assert "macd_signal" in macd_df
    assert "macd_histogram" in macd_df
    assert len(macd_df) == 30

    bb_df = compute_bollinger_bands(df)
    assert isinstance(bb_df, pd.DataFrame)
    assert "bb_upper" in bb_df
    assert "bb_middle" in bb_df
    assert "bb_lower" in bb_df
    assert len(bb_df) == 30

    atr = compute_atr(df)
    assert isinstance(atr, pd.Series)
    assert len(atr) == 30

    # Test aggregate function
    all_ind = compute_all_indicators(df)
    assert isinstance(all_ind, dict)
    assert "rsi" in all_ind
    assert "macd" in all_ind
    assert "bb_upper" in all_ind
    assert "atr" in all_ind
