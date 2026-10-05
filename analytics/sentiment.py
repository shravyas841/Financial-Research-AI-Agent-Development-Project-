from __future__ import annotations

from collections import Counter
from typing import Any

from textblob import TextBlob


def sentiment_label(polarity: float) -> str:
    if polarity > 0.1:
        return "Positive"
    if polarity < -0.1:
        return "Negative"
    return "Neutral"


def analyze_article(article: dict[str, Any]) -> dict[str, Any]:
    title = str(article.get("title") or "Untitled")
    description = str(article.get("description") or "")
    polarity = float(TextBlob(f"{title} {description}").sentiment.polarity)
    source = article.get("source") or {}
    return {
        "title": title,
        "description": description,
        "url": str(article.get("url") or ""),
        "source": str(source.get("name") or "Unknown"),
        "published_at": article.get("publishedAt"),
        "polarity": polarity,
        "label": sentiment_label(polarity),
    }


def aggregate_sentiment(articles: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    analyzed = [analyze_article(article) for article in articles]
    counts = Counter(item["label"] for item in analyzed)
    average = sum(item["polarity"] for item in analyzed) / len(analyzed) if analyzed else None
    return analyzed, {
        "article_count": len(analyzed),
        "average_score": average,
        "positive": counts["Positive"],
        "neutral": counts["Neutral"],
        "negative": counts["Negative"],
    }
