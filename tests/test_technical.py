import numpy as np
import pandas as pd
import pytest

from analytics.technical import (
    add_indicators,
    calculate_macd,
    calculate_period_return,
    calculate_rsi,
    calculate_sma,
)


def test_sma_uses_requested_window():
    result = calculate_sma(pd.Series([1, 2, 3, 4]), 3)
    assert np.isnan(result.iloc[1])
    assert result.iloc[2] == pytest.approx(2.0)
    assert result.iloc[3] == pytest.approx(3.0)


def test_rsi_is_bounded_and_rising_series_reaches_100():
    result = calculate_rsi(pd.Series(range(1, 40)), 14).dropna()
    assert result.between(0, 100).all()
    assert result.iloc[-1] == pytest.approx(100.0)


def test_macd_returns_aligned_series():
    prices = pd.Series(range(1, 60), dtype=float)
    macd, signal = calculate_macd(prices)
    assert len(macd) == len(prices)
    assert len(signal) == len(prices)
    assert macd.iloc[-1] > 0


def test_period_return():
    assert calculate_period_return(pd.Series([100.0, 110.0])) == pytest.approx(10.0)


def test_add_indicators_does_not_mutate_input():
    frame = pd.DataFrame({"Close": np.linspace(100, 150, 60)})
    result = add_indicators(frame)
    assert "SMA20" not in frame
    assert {"SMA20", "SMA50", "MACD", "MACD_SIGNAL", "RSI14", "BB_UPPER", "BB_LOWER"}.issubset(result)
