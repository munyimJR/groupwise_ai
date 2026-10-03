"""Split strategies. Deterministic: shares always sum exactly to the expense amount.

The MVP UI uses equal splits; percentage and exact-amount splits are implemented and tested
so the product can expose them without changing the data model.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence


class SplitError(ValueError):
    pass


def _dedupe(ids: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def equal_split(amount_paisa: int, participant_ids: Sequence[str]) -> dict[str, int]:
    """Split equally; leftover paisa go one each to the first participants in the given order."""
    participants = _dedupe(participant_ids)
    if not participants:
        raise SplitError("At least one participant is required.")
    base, remainder = divmod(amount_paisa, len(participants))
    return {pid: base + (1 if idx < remainder else 0) for idx, pid in enumerate(participants)}


def percentage_split(amount_paisa: int, percentages: Mapping[str, float]) -> dict[str, int]:
    if not percentages:
        raise SplitError("At least one participant is required.")
    if any(p < 0 for p in percentages.values()):
        raise SplitError("Percentages cannot be negative.")
    total_pct = sum(percentages.values())
    if abs(total_pct - 100.0) > 0.01:
        raise SplitError(f"Percentages must add up to 100 (got {total_pct:.2f}).")
    # Largest-remainder method so the shares sum exactly to the amount.
    raw = {pid: amount_paisa * pct / 100.0 for pid, pct in percentages.items()}
    shares = {pid: int(v) for pid, v in raw.items()}
    leftover = amount_paisa - sum(shares.values())
    for pid in sorted(raw, key=lambda k: (raw[k] - shares[k]), reverse=True)[:leftover]:
        shares[pid] += 1
    return shares


def exact_split(amount_paisa: int, amounts: Mapping[str, int]) -> dict[str, int]:
    if not amounts:
        raise SplitError("At least one participant is required.")
    if any(v < 0 for v in amounts.values()):
        raise SplitError("Shares cannot be negative.")
    if sum(amounts.values()) != amount_paisa:
        raise SplitError("Custom shares must add up exactly to the expense amount.")
    return dict(amounts)


def compute_split(
    method: str,
    amount_paisa: int,
    participant_ids: Sequence[str],
    weights: Mapping[str, float] | None = None,
) -> dict[str, int]:
    if method == "equal":
        return equal_split(amount_paisa, participant_ids)
    if method == "percentage":
        return percentage_split(amount_paisa, weights or {})
    if method == "exact":
        return exact_split(amount_paisa, {k: int(v) for k, v in (weights or {}).items()})
    raise SplitError(f"Unsupported split method: {method}")
