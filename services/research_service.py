from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from ai.schemas import (
    CompanySnapshot,
    FundamentalSnapshot,
    MarketSnapshot,
    ResearchSnapshot,
    RiskSnapshot,
    SentimentSnapshot,
    SnapshotMetadata,
    TechnicalSnapshot,
)
from services.market_service import MarketResearch
from services.news_service import NewsResearch


IST = ZoneInfo("Asia/Kolkata")


def build_research_snapshot(
    market: MarketResearch,
    news: NewsResearch | None,
    analysis_period: str,
    *,
    generated_at: datetime | None = None,
) -> ResearchSnapshot:
    now = generated_at or datetime.now(IST)
    sentiment = news.summary if news else {
        "article_count": 0,
        "average_score": None,
        "positive": 0,
        "neutral": 0,
        "negative": 0,
    }
    info = market.info
    return ResearchSnapshot(
        company=CompanySnapshot(
            name=info.get("shortName"),
            symbol=market.symbol,
            sector=info.get("sector"),
            industry=info.get("industry"),
        ),
        market=MarketSnapshot(**market.market),
        technical=TechnicalSnapshot(**market.technical),
        fundamentals=FundamentalSnapshot(**market.fundamentals),
        risk=RiskSnapshot(**market.risk),
        sentiment=SentimentSnapshot(**sentiment),
        metadata=SnapshotMetadata(
            market_data_source="Yahoo Finance",
            news_source="NewsAPI" if news else None,
            market_data_timestamp=now,
            news_timestamp=now if news else None,
            generated_at=now,
            analysis_period=analysis_period,
            methodology=(
                "Prices and fundamentals from Yahoo Finance; technical and risk metrics calculated "
                "deterministically in Python; news polarity calculated with TextBlob."
            ),
        ),
    )
