from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from services.market_service import MarketResearch
from utils.formatting import format_number


def price_figure(research: MarketResearch) -> go.Figure:
    data = research.prices
    figure = go.Figure()
    figure.add_trace(go.Candlestick(
        x=data["date"], open=data["Open"], high=data["High"], low=data["Low"], close=data["Close"], name="Price"
    ))
    figure.add_trace(go.Scatter(x=data["date"], y=data["SMA20"], name="SMA 20"))
    figure.add_trace(go.Scatter(x=data["date"], y=data["SMA50"], name="SMA 50"))
    figure.add_trace(go.Scatter(x=data["date"], y=data["BB_UPPER"], name="Bollinger upper", line={"dash": "dot"}))
    figure.add_trace(go.Scatter(x=data["date"], y=data["BB_LOWER"], name="Bollinger lower", line={"dash": "dot"}))
    figure.update_layout(title=f"{research.symbol} price and trend indicators", xaxis_rangeslider_visible=False, height=520)
    return figure


def indicator_figure(research: MarketResearch) -> go.Figure:
    data = research.prices
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=data["date"], y=data["MACD"], name="MACD"))
    figure.add_trace(go.Scatter(x=data["date"], y=data["MACD_SIGNAL"], name="Signal"))
    figure.update_layout(title="MACD", height=320)
    return figure


def render_verified_research(research: MarketResearch, period: str) -> None:
    st.subheader("Verified Financial Data")
    st.caption(f"Source: Yahoo Finance · Analysis period: {period} · Currency follows the selected Yahoo Finance listing")
    current, change, period_return, volatility = st.columns(4)
    current.metric("Current price", format_number(research.market["current_price"]))
    change.metric("Daily change", format_number(research.market["daily_change_pct"], suffix="%"))
    period_return.metric("Period return", format_number(research.market["period_return_pct"], suffix="%"))
    volatility.metric("Annualized volatility", format_number(research.risk["volatility_pct"], suffix="%"))
    st.plotly_chart(price_figure(research), width="stretch")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(indicator_figure(research), width="stretch")
        st.markdown("#### Calculated technical metrics")
        st.dataframe({"Metric": list(research.technical), "Value": [format_number(v) for v in research.technical.values()]}, hide_index=True)
    with right:
        st.markdown("#### Retrieved fundamentals")
        st.write(f"**Company:** {research.info.get('shortName') or 'Unavailable'}")
        st.write(f"**Sector:** {research.info.get('sector') or 'Unavailable'}")
        st.write(f"**Industry:** {research.info.get('industry') or 'Unavailable'}")
        st.dataframe({"Metric": list(research.fundamentals), "Value": [format_number(v) for v in research.fundamentals.values()]}, hide_index=True)
        st.markdown("#### Calculated risk metrics")
        st.dataframe({"Metric": list(research.risk), "Value": [format_number(v) for v in research.risk.values()]}, hide_index=True)
