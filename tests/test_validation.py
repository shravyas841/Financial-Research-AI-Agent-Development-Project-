from datetime import date

import pytest

from utils.validation import (
    make_full_symbol,
    validate_date,
    validate_positive_number,
    validate_symbol,
    validate_transaction_type,
)


def test_valid_symbol_is_normalized():
    assert validate_symbol(" reliance.ns ") == "RELIANCE.NS"
    assert validate_symbol("^nsei") == "^NSEI"
    assert make_full_symbol("tcs", "NSE (.NS)") == "TCS.NS"


@pytest.mark.parametrize("value", ["", "ABC DEF", "'; DROP TABLE transactions;--", "A" * 21])
def test_invalid_and_sql_injection_symbols_are_rejected(value):
    with pytest.raises(ValueError):
        validate_symbol(value)


def test_invalid_transaction_values_are_rejected():
    with pytest.raises(ValueError):
        validate_transaction_type("DIVIDEND")
    with pytest.raises(ValueError):
        validate_positive_number(0, "Quantity")
    with pytest.raises(ValueError):
        validate_positive_number(-1, "Price", allow_zero=True)


def test_date_validation():
    assert validate_date(date(2026, 10, 5)) == "2026-10-05"
    with pytest.raises(ValueError):
        validate_date("05/10/2026")
