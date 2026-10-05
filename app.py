from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

import streamlit as st

from ai.research_agent import AIAnalysisError, AIConfigurationError, generate_research_analysis
from ai.schemas import AIAnalysis, ResearchSnapshot
from clients.newsapi_client import NewsAPIClient, NewsAPIError
from clients.yahoo_client import MarketDataError, YahooClient
from config.settings import get_settings
from data.database import Database
from data.repositories import TransactionRepository, WatchlistRepository
from services.market_service import MarketResearch, MarketService
from services.news_service import NewsResearch, NewsService
from services.portfolio_service import PortfolioService
from services.research_service import build_research_snapshot
from ui.comparison import render_comparison
from ui.news import render_news
from ui.portfolio import render_portfolio, render_watchlist
from ui.reports import render_report_download
from ui.stock import render_verified_research
from utils.formatting import format_number
from utils.logging import configure_logging, get_logger
from utils.validation import make_full_symbol


configure_logging()
logger = get_logger(__name__)


@st.cache_data(ttl=get_settings().fundamentals_cache_ttl, show_spinner=False)
def load_fundamentals(symbol: str) -> dict:
    try:
        return YahooClient().info(symbol)
    except MarketDataError:
        return {}


@st.cache_data(ttl=get_settings().market_cache_ttl, show_spinner=False)
def load_market_research(symbol: str, period: str, interval: str) -> MarketResearch:
    service = MarketService()
    research = service.research(symbol, period, interval, info=load_fundamentals(symbol))
    service.add_benchmark_beta(research)
    return research


@st.cache_data(ttl=get_settings().news_cache_ttl, show_spinner=False)
def load_news_research(symbol: str) -> NewsResearch:
    settings = get_settings()
    client = NewsAPIClient(settings.news_api_key, settings.request_timeout)
    return NewsService(client).research(symbol)


def market_status() -> str:
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    if now.weekday() >= 5:
        return "Indian markets are closed for the weekend."
    if time(9, 15) <= now.time() <= time(15, 30):
        return "Indian cash-market trading hours are currently open (holiday calendar not checked)."
    return "Indian cash-market trading hours are currently closed."


def try_load_news(symbol: str) -> tuple[NewsResearch | None, str | None]:
    try:
        return load_news_research(symbol), None
    except NewsAPIError as exc:
        return None, str(exc)


def make_snapshot(symbol: str, period: str, interval: str) -> tuple[ResearchSnapshot, MarketResearch, NewsResearch | None, str | None]:
    market = load_market_research(symbol, period, interval)
    news, news_error = try_load_news(symbol)
    snapshot = build_research_snapshot(market, news, period)
    return snapshot, market, news, news_error


def render_snapshot_summary(snapshot: ResearchSnapshot) -> None:
    st.markdown("### Verified Financial Data")
    st.caption(
        f"Source: {snapshot.metadata.market_data_source} · Retrieved: "
        f"{snapshot.metadata.generated_at.strftime('%d %b %Y, %H:%M %Z')} · "
        f"Analysis period: {snapshot.metadata.analysis_period}"
    )
    a, b, c, d = st.columns(4)
    a.metric("Current price", format_number(snapshot.market.current_price))
    b.metric("Period return", format_number(snapshot.market.period_return_pct, suffix="%"))
    c.metric("RSI (14)", format_number(snapshot.technical.rsi_14))
    d.metric("Volatility", format_number(snapshot.risk.volatility_pct, suffix="%"))
    with st.expander("View validated ResearchSnapshot"):
        st.json(snapshot.model_dump(mode="json"))


def render_ai_analysis(analysis: AIAnalysis) -> None:
    st.markdown("### AI Research Interpretation")
    st.caption("Generated only from the validated ResearchSnapshot; not personalized investment advice.")
    st.markdown("#### Summary")
    st.write(analysis.summary)
    for title, value in [
        ("Technical analysis", analysis.technical_analysis),
        ("Fundamental analysis", analysis.fundamental_analysis),
        ("Sentiment analysis", analysis.sentiment_analysis),
        ("Risk analysis", analysis.risk_analysis),
    ]:
        st.markdown(f"#### {title}")
        st.write(value)
    st.markdown("#### Key observations")
    for item in analysis.key_observations:
        st.write(f"- {item}")
    st.markdown("#### Limitations")
    for item in analysis.limitations:
        st.write(f"- {item}")


def main() -> None:
    st.set_page_config(page_title="Financial Research AI Agent", page_icon="📊", layout="wide")
    settings = get_settings()
    database = Database(settings.database_path)
    database.initialize()
    watchlist_repository = WatchlistRepository(database)
    transaction_repository = TransactionRepository(database)

    st.title("📊 Financial Research AI Agent — Version 2")
    st.caption("Deterministic financial facts, grounded AI interpretation, and local SQLite persistence.")

    with st.sidebar:
        st.header("Research Settings")
        base_symbol = st.text_input("Base symbol", "RELIANCE")
        exchange = st.selectbox("Exchange", ["NSE (.NS)", "BSE (.BO)"])
        period = st.selectbox("Analysis period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2)
        interval = st.selectbox("Price interval", ["1d", "1wk", "1mo"])
        st.divider()
        page = st.radio(
            "Navigation",
            ["Dashboard", "Stock Research", "Comparison", "News & Sentiment", "Portfolio", "Watchlist", "AI Research Analysis", "Reports", "About"],
        )
    try:
        symbol = make_full_symbol(base_symbol, exchange)
    except ValueError as exc:
        st.error(str(exc))
        return

    try:
        if page == "Dashboard":
            st.info(market_status())
            render_verified_research(load_market_research(symbol, period, interval), period)
        elif page == "Stock Research":
            render_verified_research(load_market_research(symbol, period, interval), period)
            if st.button("Add to watchlist"):
                watchlist_repository.add(symbol)
                st.success(f"Added {symbol} to the watchlist.")
        elif page == "News & Sentiment":
            news, error = try_load_news(symbol)
            if error:
                st.warning(error)
                st.info("Add NEWS_API_KEY to your local .env file and restart Streamlit to enable news.")
            elif news:
                render_news(news)
        elif page == "Comparison":
            st.subheader("Compare Stocks")
            left, right = st.columns(2)
            with left:
                first_base = st.text_input("First symbol", base_symbol)
                first_exchange = st.selectbox("First exchange", ["NSE (.NS)", "BSE (.BO)"], key="first_exchange")
            with right:
                second_base = st.text_input("Second symbol", "TCS")
                second_exchange = st.selectbox("Second exchange", ["NSE (.NS)", "BSE (.BO)"], key="second_exchange")
            if st.button("Compare"):
                render_comparison(
                    load_market_research(make_full_symbol(first_base, first_exchange), period, "1d"),
                    load_market_research(make_full_symbol(second_base, second_exchange), period, "1d"),
                    period,
                )
        elif page == "Portfolio":
            render_portfolio(PortfolioService(transaction_repository), transaction_repository)
        elif page == "Watchlist":
            render_watchlist(watchlist_repository)
        elif page == "AI Research Analysis":
            snapshot, _, _, news_error = make_snapshot(symbol, period, interval)
            render_snapshot_summary(snapshot)
            if news_error:
                st.info(f"News was excluded from this snapshot: {news_error}")
            if st.button("Generate AI Research Analysis", type="primary"):
                with st.spinner("Generating grounded analysis..."):
                    analysis = generate_research_analysis(
                        snapshot,
                        settings.cohere_api_key,
                        settings.cohere_model,
                        settings.request_timeout * 3,
                    )
                st.session_state["latest_snapshot"] = snapshot
                st.session_state["latest_analysis"] = analysis
            analysis = st.session_state.get("latest_analysis")
            saved_snapshot = st.session_state.get("latest_snapshot")
            if analysis and saved_snapshot and saved_snapshot.company.symbol == symbol:
                render_ai_analysis(analysis)
        elif page == "Reports":
            snapshot, _, _, news_error = make_snapshot(symbol, period, interval)
            render_snapshot_summary(snapshot)
            if news_error:
                st.info(f"Report news section is unavailable: {news_error}")
            analysis = st.session_state.get("latest_analysis")
            saved_snapshot = st.session_state.get("latest_snapshot")
            matching_analysis = analysis if saved_snapshot and saved_snapshot.company.symbol == symbol else None
            if matching_analysis:
                st.success("The latest matching grounded AI analysis will be included.")
            else:
                st.info("No matching AI analysis is available; the report will contain verified data only.")
            render_report_download(snapshot, matching_analysis)
        else:
            st.subheader("About")
            st.markdown(
                """This local research application separates deterministic financial computation from AI interpretation.
                Yahoo Finance and NewsAPI data are validated, calculations are performed in Python, and the resulting
                typed ResearchSnapshot is the only financial context sent to the one-shot AI analysis feature.

                It does not execute trades, predict guaranteed returns, or provide personalized investment advice."""
            )
    except MarketDataError as exc:
        st.error(str(exc))
    except (AIConfigurationError, AIAnalysisError) as exc:
        st.error(str(exc))
    except ValueError as exc:
        st.error(str(exc))
    except Exception:
        logger.exception("Unexpected application error")
        st.error("An unexpected error occurred. See the local application log for details.")


if __name__ == "__main__":
    main()
