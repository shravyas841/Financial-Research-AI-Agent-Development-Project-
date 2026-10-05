from __future__ import annotations

from typing import Any

import requests

from utils.logging import get_logger


logger = get_logger(__name__)


class NewsAPIError(RuntimeError):
    pass


class NewsAPIConfigurationError(NewsAPIError):
    pass


class NewsAPIRateLimitError(NewsAPIError):
    pass


class NewsAPIClient:
    ENDPOINT = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout

    def search(self, query: str, page_size: int = 10) -> list[dict[str, Any]]:
        if not self.api_key:
            raise NewsAPIConfigurationError("NEWS_API_KEY is not configured in .env")
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": max(1, min(int(page_size), 100)),
        }
        headers = {"X-Api-Key": self.api_key}
        try:
            response = requests.get(self.ENDPOINT, params=params, headers=headers, timeout=self.timeout)
            if response.status_code == 429:
                logger.warning("NewsAPI rate limit reached")
                raise NewsAPIRateLimitError("NewsAPI request limit reached; try again later")
            if response.status_code in {401, 403}:
                raise NewsAPIConfigurationError("NewsAPI rejected the configured API key")
            response.raise_for_status()
            payload = response.json()
        except (NewsAPIError, NewsAPIConfigurationError):
            raise
        except requests.Timeout as exc:
            raise NewsAPIError("NewsAPI request timed out") from exc
        except (requests.RequestException, ValueError) as exc:
            logger.warning("NewsAPI request failed: %s", type(exc).__name__)
            raise NewsAPIError("NewsAPI is currently unavailable") from exc
        if not isinstance(payload, dict) or payload.get("status") != "ok":
            raise NewsAPIError("NewsAPI returned an invalid response")
        articles = payload.get("articles", [])
        if not isinstance(articles, list):
            raise NewsAPIError("NewsAPI returned malformed article data")
        return [article for article in articles if isinstance(article, dict)]
