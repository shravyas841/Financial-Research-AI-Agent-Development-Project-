from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf

from utils.logging import get_logger
from utils.validation import validate_symbol


logger = get_logger(__name__)


class MarketDataError(RuntimeError):
    pass


class YahooClient:
    def history(self, symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        normalized = validate_symbol(symbol)
        logger.info("Market data requested for %s", normalized)
        try:
            data = yf.Ticker(normalized).history(period=period, interval=interval, auto_adjust=False)
        except Exception as exc:
            logger.exception("Yahoo Finance history request failed for %s", normalized)
            raise MarketDataError("Yahoo Finance is currently unavailable") from exc
        if data is None or data.empty:
            raise MarketDataError(f"No market data was available for {normalized}")
        result = data.reset_index()
        date_column = "Datetime" if "Datetime" in result.columns else "Date"
        result = result.rename(columns={date_column: "date"})
        required = {"date", "Open", "High", "Low", "Close", "Volume"}
        if not required.issubset(result.columns):
            raise MarketDataError("Yahoo Finance returned malformed market data")
        return result

    def info(self, symbol: str) -> dict[str, Any]:
        normalized = validate_symbol(symbol)
        try:
            info = yf.Ticker(normalized).info
        except Exception as exc:
            logger.exception("Yahoo Finance fundamentals request failed for %s", normalized)
            raise MarketDataError("Company fundamentals are currently unavailable") from exc
        return info if isinstance(info, dict) else {}
