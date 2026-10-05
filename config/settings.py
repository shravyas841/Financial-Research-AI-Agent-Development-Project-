from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class Settings:
    news_api_key: str
    cohere_api_key: str
    cohere_model: str
    database_url: str
    request_timeout: int
    market_cache_ttl: int
    fundamentals_cache_ttl: int
    news_cache_ttl: int

    @property
    def database_path(self) -> Path:
        prefix = "sqlite:///"
        value = self.database_url
        if not value.startswith(prefix):
            raise ValueError("Only sqlite:/// DATABASE_URL values are supported")
        raw_path = value[len(prefix) :]
        path = Path(raw_path)
        return path if path.is_absolute() else PROJECT_ROOT / path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        news_api_key=os.getenv("NEWS_API_KEY", "").strip(),
        cohere_api_key=os.getenv("COHERE_API_KEY", "").strip(),
        cohere_model=os.getenv("COHERE_MODEL", "command-a-03-2025").strip(),
        database_url=os.getenv("DATABASE_URL", "sqlite:///financial_agent.db").strip(),
        request_timeout=_positive_int("REQUEST_TIMEOUT", 10),
        market_cache_ttl=_positive_int("MARKET_CACHE_TTL", 600),
        fundamentals_cache_ttl=_positive_int("FUNDAMENTALS_CACHE_TTL", 10800),
        news_cache_ttl=_positive_int("NEWS_CACHE_TTL", 600),
    )
