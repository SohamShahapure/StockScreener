"""
Technical indicator math, kept dependency-free (plain pandas .ewm) rather than
pulling in pandas_ta / TA-Lib, which have flaky version compatibility with
newer numpy/pandas. This is the exact formula those libraries use anyway.
"""
import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def compute_indicators(df: pd.DataFrame) -> dict:
    """
    df must have a 'Close' column (this is what yfinance .history() returns).
    Returns current price, EMA50, EMA200, and a simple trend read.
    """
    close = df["Close"]

    ema50_series = _ema(close, 50)
    ema200_series = _ema(close, 200)

    current_price = float(close.iloc[-1])

    # EMA needs at least `span` data points to be meaningful; with fewer,
    # pandas still computes a value but it's not a reliable EMA yet.
    ema50 = float(ema50_series.iloc[-1]) if len(close) >= 50 else None
    ema200 = float(ema200_series.iloc[-1]) if len(close) >= 200 else None

    trend_signal = None
    golden_cross = None
    if ema50 is not None and ema200 is not None:
        golden_cross = ema50 > ema200
        trend_signal = "bullish" if golden_cross else "bearish"

    return {
        "current_price": round(current_price, 2),
        "ema50": round(ema50, 2) if ema50 is not None else None,
        "ema200": round(ema200, 2) if ema200 is not None else None,
        "trend_signal": trend_signal,
        "golden_cross": golden_cross,
    }
