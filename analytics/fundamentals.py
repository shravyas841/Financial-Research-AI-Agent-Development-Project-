from __future__ import annotations

from typing import Any

from utils.formatting import optional_float


def extract_fundamentals(info: dict[str, Any] | None) -> dict[str, float | None]:
    source = info or {}
    return {
        "pe_ratio": optional_float(source.get("trailingPE")),
        "pb_ratio": optional_float(source.get("priceToBook")),
        "debt_to_equity": optional_float(source.get("debtToEquity")),
        "market_cap": optional_float(source.get("marketCap")),
        "revenue_growth": optional_float(source.get("revenueGrowth")),
        "profit_margin": optional_float(source.get("profitMargins")),
    }
