from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS watchlist (
                    symbol TEXT PRIMARY KEY
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT UNIQUE,
                    symbol TEXT NOT NULL,
                    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('BUY', 'SELL')),
                    quantity REAL NOT NULL CHECK (quantity > 0),
                    price REAL NOT NULL CHECK (price >= 0),
                    transaction_date TEXT NOT NULL,
                    fees REAL NOT NULL DEFAULT 0 CHECK (fees >= 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_transactions_symbol_date
                    ON transactions(symbol, transaction_date, id);
                """
            )
            self._migrate_legacy_portfolio(connection)

    @staticmethod
    def _migrate_legacy_portfolio(connection: sqlite3.Connection) -> None:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='portfolio'"
        ).fetchone()
        if not exists:
            return
        rows = connection.execute("SELECT symbol, shares, avg_price FROM portfolio").fetchall()
        for row in rows:
            if float(row["shares"]) <= 0 or float(row["avg_price"]) < 0:
                continue
            connection.execute(
                """
                INSERT OR IGNORE INTO transactions
                    (idempotency_key, symbol, transaction_type, quantity, price, transaction_date, fees)
                VALUES (?, ?, 'BUY', ?, ?, date('now'), 0)
                """,
                (f"legacy-portfolio:{row['symbol']}", row["symbol"], row["shares"], row["avg_price"]),
            )
