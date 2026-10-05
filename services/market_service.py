from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from analytics.fundamentals import extract_fundamentals
from analytics.risk import (
    calculate_beta,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_volatility,
)
from analytics.technical import add_indicators, calculate_period_return
from clients.yahoo_client import MarketDataError, YahooClient
from utils.formatting import optional_float


@dataclass
class MarketResearch:
    symbol: str
    prices: pd.DataFrame
    info: dict[str, Any]
    fundamentals: dict[str, float | None]
    market: dict[str, float | None]
    technical: dict[str, float | None]
    risk: dict[str, float | None]


class MarketService:
    def __init__(self, client: YahooClient | None = None):
        self.client = client or YahooClient()

    def research(
        self,
        symbol: str,
        period: str,
        interval: str = "1d",
        info: dict[str, Any] | None = None,
    ) -> MarketResearch:
        prices = add_indicators(self.client.history(symbol, period=period, interval=interval))
        if info is None:
            try:
                info = self.client.info(symbol)
            except MarketDataError:
                info = {}
        close = prices["Close"].astype(float)
        daily_change = None
        if len(close.dropna()) >= 2 and close.iloc[-2] != 0:
            daily_change = float((close.iloc[-1] / close.iloc[-2] - 1) * 100)
        last = prices.iloc[-1]
        technical = {
            "rsi_14": optional_float(last.get("RSI14")),
            "sma_20": optional_float(last.get("SMA20")),
            "sma_50": optional_float(last.get("SMA50")),
            "macd": optional_float(last.get("MACD")),
            "macd_signal": optional_float(last.get("MACD_SIGNAL")),
            "bollinger_upper": optional_float(last.get("BB_UPPER")),
            "bollinger_lower": optional_float(last.get("BB_LOWER")),
        }
        return MarketResearch(
            symbol=symbol,
            prices=prices,
            info=info,
            fundamentals=extract_fundamentals(info),
            market={
                "current_price": optional_float(close.iloc[-1]),
                "daily_change_pct": daily_change,
                "period_return_pct": calculate_period_return(close),
            },
            technical=technical,
            risk={
                "volatility_pct": calculate_volatility(close),
                "max_drawdown_pct": calculate_max_drawdown(close),
                "sharpe_ratio": calculate_sharpe_ratio(close),
                "beta": None,
            },
        )

    def add_benchmark_beta(self, research: MarketResearch, benchmark_symbol: str = "^NSEI") -> None:
        try:
            benchmark = self.client.history(benchmark_symbol, period="1y", interval="1d")
            asset = research.prices.set_index("date")["Close"]
            index_prices = benchmark.set_index("date")["Close"]
            research.risk["beta"] = calculate_beta(asset, index_prices)
        except MarketDataError:
            research.risk["beta"] = None
