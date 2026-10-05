from __future__ import annotations

import math
from typing import Any


def optional_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) or math.isinf(number) else number


def format_number(value: float | None, decimals: int = 2, suffix: str = "") -> str:
    return "Unavailable" if value is None else f"{value:,.{decimals}f}{suffix}"
