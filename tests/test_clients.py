import pytest

from clients.newsapi_client import NewsAPIClient, NewsAPIConfigurationError, NewsAPIRateLimitError


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")

    def json(self):
        return self.payload


def test_news_client_requires_key():
    with pytest.raises(NewsAPIConfigurationError):
        NewsAPIClient("").search("TCS")


def test_news_client_uses_header_params_and_timeout(monkeypatch):
    captured = {}

    def fake_get(url, *, params, headers, timeout):
        captured.update(url=url, params=params, headers=headers, timeout=timeout)
        return FakeResponse(200, {"status": "ok", "articles": [{"title": "Example"}]})

    monkeypatch.setattr("clients.newsapi_client.requests.get", fake_get)
    result = NewsAPIClient("secret", timeout=7).search("TCS", page_size=10)
    assert result[0]["title"] == "Example"
    assert "secret" not in captured["url"]
    assert captured["headers"] == {"X-Api-Key": "secret"}
    assert captured["timeout"] == 7


def test_news_client_handles_rate_limit(monkeypatch):
    monkeypatch.setattr(
        "clients.newsapi_client.requests.get",
        lambda *args, **kwargs: FakeResponse(429, {}),
    )
    with pytest.raises(NewsAPIRateLimitError):
        NewsAPIClient("secret").search("TCS")
