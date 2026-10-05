from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from pydantic import ValidationError

from ai.research_agent import (
    AIAnalysisError,
    AIConfigurationError,
    _assert_missing_metrics_not_invented,
    build_input,
    generate_research_analysis,
)
from ai.schemas import AIAnalysis, ResearchSnapshot, SentimentSnapshot
from services.market_service import MarketResearch
from services.research_service import build_research_snapshot


def snapshot() -> ResearchSnapshot:
    market = MarketResearch(
        symbol="TEST.NS",
        prices=pd.DataFrame({"Close": [100, 110]}),
        info={"shortName": "Test Ltd", "sector": "Technology"},
        fundamentals={"pe_ratio": None, "pb_ratio": 2.0, "debt_to_equity": None, "market_cap": 1000.0, "revenue_growth": None, "profit_margin": None},
        market={"current_price": 110.0, "daily_change_pct": 1.0, "period_return_pct": 10.0},
        technical={"rsi_14": 55.0, "sma_20": 105.0, "sma_50": None, "macd": 1.2, "macd_signal": 1.0, "bollinger_upper": 115.0, "bollinger_lower": 95.0},
        risk={"volatility_pct": 20.0, "max_drawdown_pct": -5.0, "sharpe_ratio": 0.7, "beta": None},
    )
    return build_research_snapshot(market, None, "6mo", generated_at=datetime(2026, 10, 5, tzinfo=ZoneInfo("Asia/Kolkata")))


def valid_analysis(**updates) -> AIAnalysis:
    values = {
        "summary": "The verified snapshot shows a current price of 110.",
        "technical_analysis": "The supplied RSI is 55.",
        "fundamental_analysis": "P/E data is unavailable in the supplied snapshot.",
        "sentiment_analysis": "No news articles were available.",
        "risk_analysis": "Volatility is 20%; beta is unavailable.",
        "key_observations": ["Period return is 10%."],
        "limitations": ["P/E and beta are unavailable."],
    }
    values.update(updates)
    return AIAnalysis(**values)


def test_snapshot_preserves_missing_fundamental_and_supplied_rsi():
    result = snapshot()
    assert result.fundamentals.pe_ratio is None
    assert result.technical.rsi_14 == 55


def test_sentiment_counts_must_match():
    with pytest.raises(ValidationError):
        SentimentSnapshot(article_count=2, average_score=0, positive=1, neutral=0, negative=0)


def test_ai_input_contains_only_prompt_and_snapshot():
    messages = build_input(snapshot())
    assert len(messages) == 2
    assert "ResearchSnapshot JSON" in messages[1]["content"]
    assert '"rsi_14": 55.0' in messages[1]["content"]


def test_grounding_accepts_explicit_unavailable_pe():
    _assert_missing_metrics_not_invented(snapshot(), valid_analysis())


def test_grounding_rejects_invented_pe():
    bad = valid_analysis(fundamental_analysis="The P/E ratio is 24.5.")
    with pytest.raises(AIAnalysisError, match="P/E"):
        _assert_missing_metrics_not_invented(snapshot(), bad)


def test_ai_requires_local_api_key_without_making_request():
    with pytest.raises(AIConfigurationError, match="COHERE_API_KEY"):
        generate_research_analysis(snapshot(), "", "command-a-03-2025")
