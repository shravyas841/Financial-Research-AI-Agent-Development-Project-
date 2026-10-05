from pathlib import Path

import pytest

from data.database import Database
from data.models import Transaction
from data.repositories import TransactionRepository, WatchlistRepository


def test_repository_is_parameterized_and_idempotent(tmp_path: Path):
    database = Database(tmp_path / "test.db")
    database.initialize()
    repository = TransactionRepository(database)
    transaction = Transaction("RELIANCE.NS", "BUY", 2, 100, "2026-10-05", 1, "same-key")
    first_id, first_created = repository.add(transaction)
    second_id, second_created = repository.add(transaction)
    assert first_created is True
    assert second_created is False
    assert first_id == second_id
    assert len(repository.list()) == 1


def test_watchlist_rejects_sql_injection(tmp_path: Path):
    database = Database(tmp_path / "test.db")
    database.initialize()
    repository = WatchlistRepository(database)
    with pytest.raises(ValueError):
        repository.add("X'; DROP TABLE watchlist;--")
    repository.add("TCS.NS")
    assert repository.list() == ["TCS.NS"]


def test_legacy_portfolio_is_migrated_once(tmp_path: Path):
    database = Database(tmp_path / "legacy.db")
    with database.connect() as connection:
        connection.execute("CREATE TABLE portfolio(symbol TEXT PRIMARY KEY, shares REAL, avg_price REAL)")
        connection.execute("INSERT INTO portfolio VALUES ('INFY.NS', 3, 1000)")
    database.initialize()
    database.initialize()
    rows = TransactionRepository(database).list()
    assert len(rows) == 1
    assert rows[0]["symbol"] == "INFY.NS"
