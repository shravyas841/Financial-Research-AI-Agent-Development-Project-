import pytest

from analytics.portfolio import build_portfolio_summary, calculate_positions, portfolio_totals


TRANSACTIONS = [
    {"id": 1, "symbol": "TEST.NS", "transaction_type": "BUY", "quantity": 10, "price": 100, "fees": 10, "transaction_date": "2026-01-01"},
    {"id": 2, "symbol": "TEST.NS", "transaction_type": "BUY", "quantity": 10, "price": 120, "fees": 10, "transaction_date": "2026-02-01"},
    {"id": 3, "symbol": "TEST.NS", "transaction_type": "SELL", "quantity": 5, "price": 130, "fees": 5, "transaction_date": "2026-03-01"},
]


def test_weighted_average_cost_and_realized_pnl():
    position = calculate_positions(TRANSACTIONS)["TEST.NS"]
    assert position.quantity == pytest.approx(15)
    assert position.average_cost == pytest.approx(111)
    assert position.realized_pnl == pytest.approx(90)


def test_unrealized_total_and_allocation():
    rows = build_portfolio_summary(TRANSACTIONS, {"TEST.NS": 140})
    assert rows[0]["Unrealized P&L"] == pytest.approx(435)
    assert rows[0]["Total P&L"] == pytest.approx(525)
    assert rows[0]["Allocation %"] == pytest.approx(100)
    totals = portfolio_totals(rows)
    assert totals["total_pnl"] == pytest.approx(525)


def test_sell_more_than_owned_is_rejected():
    with pytest.raises(ValueError, match="Cannot sell"):
        calculate_positions([
            {"id": 1, "symbol": "TEST.NS", "transaction_type": "BUY", "quantity": 1, "price": 100, "fees": 0, "transaction_date": "2026-01-01"},
            {"id": 2, "symbol": "TEST.NS", "transaction_type": "SELL", "quantity": 2, "price": 120, "fees": 0, "transaction_date": "2026-01-02"},
        ])
