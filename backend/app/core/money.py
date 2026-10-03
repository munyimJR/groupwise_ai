"""Exact money helpers. All internal arithmetic is integer paisa."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

MAX_AMOUNT_PAISA = 100_000_000_00  # ৳10 crore — sanity bound for a shared-expense app


class MoneyError(ValueError):
    pass


def to_paisa(amount: float | int | str | Decimal) -> int:
    try:
        value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise MoneyError(f"Invalid amount: {amount!r}") from exc
    paisa = int(value * 100)
    if paisa <= 0:
        raise MoneyError("Amount must be greater than zero.")
    if paisa > MAX_AMOUNT_PAISA:
        raise MoneyError("Amount is unrealistically large for a shared expense.")
    return paisa


def to_taka(paisa: int | float) -> float:
    return round(paisa / 100, 2)


def fmt_taka(paisa: int | float, decimals: int = 0) -> str:
    """Human formatting used in explanations, e.g. 825000 -> '৳8,250'."""
    value = paisa / 100
    if decimals == 0:
        return f"৳{round(value):,}"
    return f"৳{value:,.{decimals}f}"
