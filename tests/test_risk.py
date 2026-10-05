import numpy as np
import pandas as pd
import pytest

from analytics.risk import calculate_beta, calculate_max_drawdown, calculate_sharpe_ratio, calculate_volatility


def test_max_drawdown():
    assert calculate_max_drawdown(pd.Series([100, 120, 90, 108])) == pytest.approx(-25.0)


def test_volatility_is_non_negative():
    result = calculate_volatility(pd.Series([100, 101, 99, 102, 100], dtype=float))
    assert result is not None and result >= 0


def test_sharpe_unavailable_for_constant_returns():
    assert calculate_sharpe_ratio(pd.Series([100.0, 100.0, 100.0])) is None


def test_beta_matches_two_x_benchmark_returns():
    benchmark_returns = np.array([0.01, -0.02, 0.03, 0.01])
    asset_returns = benchmark_returns * 2
    benchmark = pd.Series(100 * np.cumprod(np.r_[1, 1 + benchmark_returns]))
    asset = pd.Series(100 * np.cumprod(np.r_[1, 1 + asset_returns]))
    assert calculate_beta(asset, benchmark) == pytest.approx(2.0)
