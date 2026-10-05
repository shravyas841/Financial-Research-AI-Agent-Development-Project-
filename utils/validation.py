from __future__ import annotations

import re
from datetime import date, datetime


SYMBOL_PATTERN = re.compile(r"^\^?[A-Z0-9&.-]{1,20}$")
SUPPORTED_TRANSACTION_TYPES = {"BUY", "SELL"}


def validate_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper()
    if not SYMBOL_PATTERN.fullmatch(cleaned):
        raise ValueError("Symbol must contain only letters, numbers, &, ., -, or a leading ^ (maximum 20 characters).")
    return cleaned


def make_full_symbol(base_symbol: str, exchange: str) -> str:
    symbol = validate_symbol(base_symbol)
    if symbol.endswith((".NS", ".BO")):
        return symbol
    suffix = {"NSE (.NS)": ".NS", "BSE (.BO)": ".BO"}.get(exchange)
    if suffix is None:
        raise ValueError("Unsupported exchange")
    return f"{symbol}{suffix}"


def validate_transaction_type(value: str) -> str:
    cleaned = value.strip().upper()
    if cleaned not in SUPPORTED_TRANSACTION_TYPES:
        raise ValueError("Transaction type must be BUY or SELL")
    return cleaned


def validate_positive_number(value: float, field_name: str, *, allow_zero: bool = False) -> float:
    number = float(value)
    valid = number >= 0 if allow_zero else number > 0
    if not valid:
        comparison = "zero or greater" if allow_zero else "greater than zero"
        raise ValueError(f"{field_name} must be {comparison}")
    return number


def validate_date(value: str | date | datetime) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError("Transaction date must use YYYY-MM-DD format") from exc
