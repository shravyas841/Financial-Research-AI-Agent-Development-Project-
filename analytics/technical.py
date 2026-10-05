from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_sma(prices: pd.Series, window: int) -> pd.Series:
    if window <= 0:
        raise ValueError("SMA window must be positive")
    return prices.astype(float).rolling(window=window, min_periods=window).mean()


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    if period <= 0:
        raise ValueError("RSI period must be positive")
    delta = prices.astype(float).diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    average_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + relative_strength))
    result = result.where(average_loss.ne(0), 100.0)
    return result.where(average_gain.ne(0) | average_loss.ne(0), 50.0)


def calculate_macd(
    prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series]:
    values = prices.astype(float)
    macd = values.ewm(span=fast, adjust=False).mean() - values.ewm(span=slow, adjust=False).mean()
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line


def calculate_bollinger_bands(
    prices: pd.Series, window: int = 20, deviations: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    middle = calculate_sma(prices, window)
    std = prices.astype(float).rolling(window=window, min_periods=window).std(ddof=0)
    return middle, middle + deviations * std, middle - deviations * std


def calculate_period_return(prices: pd.Series) -> float | None:
    clean = prices.dropna().astype(float)
    if len(clean) < 2 or clean.iloc[0] == 0:
        return None
    return float((clean.iloc[-1] / clean.iloc[0] - 1) * 100)


def add_indicators(data: pd.DataFrame) -> pd.DataFrame:
    if "Close" not in data:
        raise ValueError("Price data must contain a Close column")
    result = data.copy()
    result["SMA20"] = calculate_sma(result["Close"], 20)
    result["SMA50"] = calculate_sma(result["Close"], 50)
    result["MACD"], result["MACD_SIGNAL"] = calculate_macd(result["Close"])
    result["RSI14"] = calculate_rsi(result["Close"], 14)
    _, result["BB_UPPER"], result["BB_LOWER"] = calculate_bollinger_bands(result["Close"])
    return result
