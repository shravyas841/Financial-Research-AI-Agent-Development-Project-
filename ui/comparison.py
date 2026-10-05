from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from services.market_service import MarketResearch


def render_comparison(first: MarketResearch, second: MarketResearch, period: str) -> None:
    figure = go.Figure()
    for research in (first, second):
        data = research.prices
        normalized = (data["Close"] / data["Close"].iloc[0] - 1) * 100
        figure.add_trace(go.Scatter(x=data["date"], y=normalized, name=research.symbol))
    figure.update_layout(title=f"Relative return comparison ({period})", xaxis_title="Date", yaxis_title="Return (%)")
    st.plotly_chart(figure, width="stretch")
