"""Glue between the snapshot and the forecast model, plus each member's expected share."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from ..ml.forecast import SpendTxn, forecast_group
from ..services.snapshot import GroupSnapshot, memo


def spend_txns(snap: GroupSnapshot) -> list[SpendTxn]:
    # Unusual one-off expenses are excluded so a single spike doesn't distort the projection.
    return [SpendTxn(e.amount, e.category, e.subcategory, e.occurred_at, e.description, e.merchant)
            for e in snap.expenses if not e.is_one_off]


def consumption_shares(snap: GroupSnapshot, days: int = 60) -> dict[str, float]:
    since = snap.as_of - timedelta(days=days)
    consumed: dict[str, int] = defaultdict(int)
    for e in snap.expenses:
        if e.occurred_at >= since:
            for mid, sh in e.shares.items():
                consumed[mid] += sh
    total = sum(consumed.values())
    active = {m.id for m in snap.active_members}
    if not total:
        return {m: 1 / len(active) for m in active} if active else {}
    return {mid: v / total for mid, v in consumed.items() if mid in active}


def group_forecast(snap: GroupSnapshot, horizon: int = 7) -> dict:
    def compute() -> dict:
        result = forecast_group(spend_txns(snap), snap.as_of.date(), horizon)
        if result.get("status") == "ok":
            shares = consumption_shares(snap)
            result["member_shares"] = sorted(
                ({"member_id": mid, "name": snap.member_name(mid), "share_pct": round(s * 100, 1),
                  "expected": round(result["total"] * s)} for mid, s in shares.items()),
                key=lambda r: -r["expected"])
            result["excluded_unusual"] = sum(1 for e in snap.expenses if e.is_one_off)
        return result

    return memo(snap, f"forecast:{horizon}", compute)
