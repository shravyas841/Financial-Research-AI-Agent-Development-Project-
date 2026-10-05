from __future__ import annotations

import math

import numpy as np
import pandas as pd


TRADING_DAYS = 252


def calculate_returns(prices: pd.Series) -> pd.Series:
    return prices.astype(float).pct_change().dropna()


def calculate_volatility(prices: pd.Series, periods_per_year: int = TRADING_DAYS) -> float | None:
    returns = calculate_returns(prices)
    if len(returns) < 2:
        return None
    return float(returns.std(ddof=1) * math.sqrt(periods_per_year) * 100)


def calculate_max_drawdown(prices: pd.Series) -> float | None:
    clean = prices.dropna().astype(float)
    if clean.empty:
        return None
    running_peak = clean.cummax()
    drawdown = clean / running_peak - 1
    return float(drawdown.min() * 100)


def calculate_sharpe_ratio(
    prices: pd.Series, annual_risk_free_rate: float = 0.0, periods_per_year: int = TRADING_DAYS
) -> float | None:
    returns = calculate_returns(prices)
    if len(returns) < 2:
        return None
    excess = returns - annual_risk_free_rate / periods_per_year
    std = excess.std(ddof=1)
    if std == 0 or np.isnan(std):
        return None
    return float(excess.mean() / std * math.sqrt(periods_per_year))


def calculate_beta(asset_prices: pd.Series, benchmark_prices: pd.Series) -> float | None:
    joined = pd.concat(
        [calculate_returns(asset_prices).rename("asset"), calculate_returns(benchmark_prices).rename("benchmark")],
        axis=1,
    ).dropna()
    if len(joined) < 2:
        return None
    variance = joined["benchmark"].var(ddof=1)
    if variance == 0 or np.isnan(variance):
        return None
    return float(joined.cov().loc["asset", "benchmark"] / variance)
