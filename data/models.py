from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Transaction:
    symbol: str
    transaction_type: str
    quantity: float
    price: float
    transaction_date: str
    fees: float = 0.0
    idempotency_key: str | None = None
