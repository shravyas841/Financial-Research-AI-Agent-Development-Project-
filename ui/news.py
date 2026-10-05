from __future__ import annotations

import pandas as pd
import streamlit as st

from services.news_service import NewsResearch
from utils.formatting import format_number


def render_news(news: NewsResearch) -> None:
    st.subheader("News & Sentiment")
    summary = news.summary
    a, b, c, d = st.columns(4)
    a.metric("Articles", summary["article_count"])
    b.metric("Average polarity", format_number(summary["average_score"]))
    c.metric("Positive", summary["positive"])
    d.metric("Negative", summary["negative"])
    st.caption("TextBlob sentiment is descriptive. It does not predict whether a stock will rise or fall.")
    if not news.articles:
        st.info("No matching news articles were returned.")
        return
    frame = pd.DataFrame(news.articles)
    st.dataframe(frame[["published_at", "source", "title", "label", "polarity"]], hide_index=True, width="stretch")
    for article in news.articles:
        st.markdown(f"**{article['title']}** — {article['source']}")
        st.caption(article.get("published_at") or "Timestamp unavailable")
        st.write(article.get("description") or "Description unavailable")
        if article.get("url"):
            st.markdown(f"[Read article]({article['url']})")
        st.divider()
