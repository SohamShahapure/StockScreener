"""
These tests use synthetic price data instead of live yfinance calls, so they
run instantly and offline (in CI, on a plane, wherever) while still proving
the EMA math and trend logic are correct.
"""
import pandas as pd
import pytest

from app.services.indicators import compute_indicators


def _make_df(prices: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"Close": prices})


def test_uptrend_produces_bullish_signal():
    # Steady climb from 100 to ~300 over 250 sessions -> EMA50 should sit
    # above EMA200 near the end, i.e. a golden cross / bullish read.
    prices = [100 + i * 0.8 for i in range(250)]
    result = compute_indicators(_make_df(prices))

    assert result["ema50"] is not None
    assert result["ema200"] is not None
    assert result["ema50"] > result["ema200"]
    assert result["trend_signal"] == "bullish"
    assert result["golden_cross"] is True


def test_downtrend_produces_bearish_signal():
    prices = [300 - i * 0.8 for i in range(250)]
    result = compute_indicators(_make_df(prices))

    assert result["trend_signal"] == "bearish"
    assert result["golden_cross"] is False


def test_insufficient_history_returns_none_for_missing_emas():
    # Only 30 data points: not enough for EMA50 or EMA200 to be meaningful.
    prices = [100 + i for i in range(30)]
    result = compute_indicators(_make_df(prices))

    assert result["ema50"] is None
    assert result["ema200"] is None
    assert result["trend_signal"] is None
    assert result["current_price"] == pytest.approx(129.0, abs=0.01)
