from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CompanySnapshot(StrictModel):
    name: str | None = None
    symbol: str
    sector: str | None = None
    industry: str | None = None


class MarketSnapshot(StrictModel):
    current_price: float | None = None
    daily_change_pct: float | None = None
    period_return_pct: float | None = None


class TechnicalSnapshot(StrictModel):
    rsi_14: float | None = Field(default=None, ge=0, le=100)
    sma_20: float | None = None
    sma_50: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    bollinger_upper: float | None = None
    bollinger_lower: float | None = None


class FundamentalSnapshot(StrictModel):
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    debt_to_equity: float | None = None
    market_cap: float | None = None
    revenue_growth: float | None = None
    profit_margin: float | None = None


class RiskSnapshot(StrictModel):
    volatility_pct: float | None = Field(default=None, ge=0)
    max_drawdown_pct: float | None = Field(default=None, le=0)
    sharpe_ratio: float | None = None
    beta: float | None = None


class SentimentSnapshot(StrictModel):
    article_count: int = Field(ge=0)
    average_score: float | None = Field(default=None, ge=-1, le=1)
    positive: int = Field(ge=0)
    neutral: int = Field(ge=0)
    negative: int = Field(ge=0)

    @model_validator(mode="after")
    def counts_match(self) -> "SentimentSnapshot":
        if self.positive + self.neutral + self.negative != self.article_count:
            raise ValueError("Sentiment counts must equal article_count")
        return self


class SnapshotMetadata(StrictModel):
    market_data_source: str
    news_source: str | None = None
    market_data_timestamp: datetime
    news_timestamp: datetime | None = None
    generated_at: datetime
    analysis_period: str
    methodology: str


class ResearchSnapshot(StrictModel):
    company: CompanySnapshot
    market: MarketSnapshot
    technical: TechnicalSnapshot
    fundamentals: FundamentalSnapshot
    risk: RiskSnapshot
    sentiment: SentimentSnapshot
    metadata: SnapshotMetadata


class AIAnalysis(StrictModel):
    summary: str
    technical_analysis: str
    fundamental_analysis: str
    sentiment_analysis: str
    risk_analysis: str
    key_observations: list[str]
    limitations: list[str]
