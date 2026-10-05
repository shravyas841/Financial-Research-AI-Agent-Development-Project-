from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass
class Position:
    symbol: str
    quantity: float = 0.0
    average_cost: float = 0.0
    realized_pnl: float = 0.0


def calculate_positions(transactions: Iterable[Mapping[str, object]]) -> dict[str, Position]:
    positions: dict[str, Position] = defaultdict(lambda: Position(symbol=""))
    ordered = sorted(transactions, key=lambda row: (str(row["transaction_date"]), int(row.get("id", 0))))
    for row in ordered:
        symbol = str(row["symbol"])
        transaction_type = str(row["transaction_type"]).upper()
        quantity = float(row["quantity"])
        price = float(row["price"])
        fees = float(row.get("fees", 0.0))
        position = positions[symbol]
        position.symbol = symbol

        if transaction_type == "BUY":
            previous_cost = position.quantity * position.average_cost
            position.quantity += quantity
            position.average_cost = (previous_cost + quantity * price + fees) / position.quantity
        elif transaction_type == "SELL":
            if quantity > position.quantity + 1e-9:
                raise ValueError(f"Cannot sell {quantity} shares of {symbol}; only {position.quantity} available")
            proceeds = quantity * price - fees
            position.realized_pnl += proceeds - quantity * position.average_cost
            position.quantity -= quantity
            if abs(position.quantity) < 1e-9:
                position.quantity = 0.0
                position.average_cost = 0.0
        else:
            raise ValueError(f"Unsupported transaction type: {transaction_type}")
    return dict(positions)


def build_portfolio_summary(
    transactions: Iterable[Mapping[str, object]], current_prices: Mapping[str, float | None]
) -> list[dict[str, float | str | None]]:
    positions = calculate_positions(transactions)
    rows: list[dict[str, float | str | None]] = []
    total_value = sum(
        position.quantity * float(current_prices[symbol])
        for symbol, position in positions.items()
        if position.quantity > 0 and current_prices.get(symbol) is not None
    )
    for symbol, position in sorted(positions.items()):
        if position.quantity <= 0 and position.realized_pnl == 0:
            continue
        current_price = current_prices.get(symbol)
        invested = position.quantity * position.average_cost
        current_value = position.quantity * float(current_price) if current_price is not None else None
        unrealized = current_value - invested if current_value is not None else None
        total_pnl = position.realized_pnl + unrealized if unrealized is not None else None
        rows.append(
            {
                "Symbol": symbol,
                "Quantity": position.quantity,
                "Average Cost": position.average_cost,
                "Current Price": current_price,
                "Invested Value": invested,
                "Current Value": current_value,
                "Realized P&L": position.realized_pnl,
                "Unrealized P&L": unrealized,
                "Total P&L": total_pnl,
                "Allocation %": (current_value / total_value * 100) if current_value is not None and total_value else None,
            }
        )
    return rows


def portfolio_totals(rows: Iterable[Mapping[str, object]]) -> dict[str, float]:
    result = {"invested": 0.0, "current_value": 0.0, "realized_pnl": 0.0, "unrealized_pnl": 0.0}
    for row in rows:
        result["invested"] += float(row.get("Invested Value") or 0.0)
        result["current_value"] += float(row.get("Current Value") or 0.0)
        result["realized_pnl"] += float(row.get("Realized P&L") or 0.0)
        result["unrealized_pnl"] += float(row.get("Unrealized P&L") or 0.0)
    result["total_pnl"] = result["realized_pnl"] + result["unrealized_pnl"]
    result["return_pct"] = result["total_pnl"] / result["invested"] * 100 if result["invested"] else 0.0
    return result
