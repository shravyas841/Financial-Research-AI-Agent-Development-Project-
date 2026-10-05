from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from data.database import Database
from data.models import Transaction
from utils.validation import (
    validate_date,
    validate_positive_number,
    validate_symbol,
    validate_transaction_type,
)


class WatchlistRepository:
    def __init__(self, database: Database):
        self.database = database

    def list(self) -> list[str]:
        with self.database.connect() as connection:
            return [row["symbol"] for row in connection.execute("SELECT symbol FROM watchlist ORDER BY symbol")]

    def add(self, symbol: str) -> None:
        value = validate_symbol(symbol)
        with self.database.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO watchlist(symbol) VALUES (?)", (value,))

    def remove(self, symbol: str) -> None:
        value = validate_symbol(symbol)
        with self.database.connect() as connection:
            connection.execute("DELETE FROM watchlist WHERE symbol = ?", (value,))


class TransactionRepository:
    def __init__(self, database: Database):
        self.database = database

    def list(self, symbol: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM transactions"
        parameters: tuple[str, ...] = ()
        if symbol is not None:
            query += " WHERE symbol = ?"
            parameters = (validate_symbol(symbol),)
        query += " ORDER BY transaction_date, id"
        with self.database.connect() as connection:
            return [dict(row) for row in connection.execute(query, parameters).fetchall()]

    def add(self, transaction: Transaction) -> tuple[int, bool]:
        symbol = validate_symbol(transaction.symbol)
        transaction_type = validate_transaction_type(transaction.transaction_type)
        quantity = validate_positive_number(transaction.quantity, "Quantity")
        price = validate_positive_number(transaction.price, "Price", allow_zero=True)
        fees = validate_positive_number(transaction.fees, "Fees", allow_zero=True)
        transaction_date = validate_date(transaction.transaction_date)
        key = transaction.idempotency_key or str(uuid.uuid4())
        try:
            with self.database.connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO transactions
                        (idempotency_key, symbol, transaction_type, quantity, price, transaction_date, fees)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (key, symbol, transaction_type, quantity, price, transaction_date, fees),
                )
                return int(cursor.lastrowid), True
        except sqlite3.IntegrityError as exc:
            if "idempotency_key" not in str(exc):
                raise
            with self.database.connect() as connection:
                row = connection.execute(
                    "SELECT id FROM transactions WHERE idempotency_key = ?", (key,)
                ).fetchone()
            return int(row["id"]), False

    def delete(self, transaction_id: int) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM transactions WHERE id = ?", (int(transaction_id),))
