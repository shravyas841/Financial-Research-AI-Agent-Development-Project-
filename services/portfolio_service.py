from __future__ import annotations

from analytics.portfolio import build_portfolio_summary, calculate_positions, portfolio_totals
from clients.yahoo_client import MarketDataError, YahooClient
from data.models import Transaction
from data.repositories import TransactionRepository


class PortfolioService:
    def __init__(self, repository: TransactionRepository, market_client: YahooClient | None = None):
        self.repository = repository
        self.market_client = market_client or YahooClient()

    def add_transaction(self, transaction: Transaction) -> tuple[int, bool]:
        existing = self.repository.list()
        trial = existing + [
            {
                "id": 10**12,
                "symbol": transaction.symbol,
                "transaction_type": transaction.transaction_type,
                "quantity": transaction.quantity,
                "price": transaction.price,
                "transaction_date": transaction.transaction_date,
                "fees": transaction.fees,
            }
        ]
        calculate_positions(trial)
        return self.repository.add(transaction)

    def summary(self) -> tuple[list[dict], dict[str, float]]:
        transactions = self.repository.list()
        positions = calculate_positions(transactions)
        prices: dict[str, float | None] = {}
        for symbol, position in positions.items():
            if position.quantity <= 0:
                prices[symbol] = None
                continue
            try:
                history = self.market_client.history(symbol, period="5d", interval="1d")
                prices[symbol] = float(history["Close"].iloc[-1])
            except MarketDataError:
                prices[symbol] = None
        rows = build_portfolio_summary(transactions, prices)
        return rows, portfolio_totals(rows)
