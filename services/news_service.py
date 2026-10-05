from __future__ import annotations

from dataclasses import dataclass

from analytics.sentiment import aggregate_sentiment
from clients.newsapi_client import NewsAPIClient


@dataclass
class NewsResearch:
    articles: list[dict]
    summary: dict


class NewsService:
    def __init__(self, client: NewsAPIClient):
        self.client = client

    def research(self, symbol: str, page_size: int = 10) -> NewsResearch:
        base_symbol = symbol.split(".")[0]
        articles = self.client.search(f"{base_symbol} stock India", page_size=page_size)
        analyzed, summary = aggregate_sentiment(articles)
        return NewsResearch(analyzed, summary)
