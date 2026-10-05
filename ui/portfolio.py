from __future__ import annotations

import uuid
from datetime import date

import pandas as pd
import streamlit as st

from data.models import Transaction
from data.repositories import TransactionRepository, WatchlistRepository
from services.portfolio_service import PortfolioService
from utils.validation import make_full_symbol


def render_watchlist(repository: WatchlistRepository) -> None:
    st.subheader("Watchlist")
    symbols = repository.list()
    st.write(symbols if symbols else "Your watchlist is empty.")
    add_col, remove_col = st.columns(2)
    with add_col, st.form("watchlist_add"):
        base = st.text_input("Base symbol", "INFY")
        exchange = st.selectbox("Exchange", ["NSE (.NS)", "BSE (.BO)"], key="watchlist_exchange")
        submitted = st.form_submit_button("Add symbol")
        if submitted:
            try:
                symbol = make_full_symbol(base, exchange)
                repository.add(symbol)
                st.success(f"Added {symbol}. Refresh or interact with the page to see the updated list.")
            except ValueError as exc:
                st.error(str(exc))
    with remove_col:
        selected = st.selectbox("Remove symbol", symbols, disabled=not symbols)
        if st.button("Remove", disabled=not symbols):
            repository.remove(selected)
            st.success(f"Removed {selected}.")


def render_portfolio(service: PortfolioService, repository: TransactionRepository) -> None:
    st.subheader("Transaction-based Portfolio")
    st.caption("Holdings, average cost, and realized/unrealized P&L are derived from immutable BUY/SELL records.")
    with st.form("transaction_form", clear_on_submit=False):
        one, two = st.columns(2)
        with one:
            base = st.text_input("Base symbol", "RELIANCE")
            exchange = st.selectbox("Exchange", ["NSE (.NS)", "BSE (.BO)"], key="portfolio_exchange")
            transaction_type = st.selectbox("Transaction type", ["BUY", "SELL"])
            transaction_date = st.date_input("Transaction date", date.today())
        with two:
            quantity = st.number_input("Quantity", min_value=0.0001, value=1.0, step=1.0)
            price = st.number_input("Price", min_value=0.0, value=100.0, step=1.0)
            fees = st.number_input("Fees", min_value=0.0, value=0.0, step=1.0)
        submitted = st.form_submit_button("Record transaction")
        if submitted:
            try:
                symbol = make_full_symbol(base, exchange)
                transaction = Transaction(
                    symbol=symbol,
                    transaction_type=transaction_type,
                    quantity=quantity,
                    price=price,
                    transaction_date=transaction_date.isoformat(),
                    fees=fees,
                    idempotency_key=str(uuid.uuid4()),
                )
                _, created = service.add_transaction(transaction)
                st.success("Transaction recorded." if created else "This transaction was already recorded.")
            except ValueError as exc:
                st.error(str(exc))

    transactions = repository.list()
    if transactions:
        st.markdown("#### Ledger")
        st.dataframe(pd.DataFrame(transactions), hide_index=True, width="stretch")
    else:
        st.info("No transactions have been recorded.")
        return
    try:
        rows, totals = service.summary()
    except ValueError as exc:
        st.error(f"Portfolio ledger is inconsistent: {exc}")
        return
    st.markdown("#### Derived positions")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    a, b, c, d = st.columns(4)
    a.metric("Invested value", f"₹{totals['invested']:,.2f}")
    b.metric("Current value", f"₹{totals['current_value']:,.2f}")
    c.metric("Total P&L", f"₹{totals['total_pnl']:,.2f}")
    d.metric("Portfolio return", f"{totals['return_pct']:.2f}%")
