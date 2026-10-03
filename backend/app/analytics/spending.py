"""AI Feature 2 — Spending intelligence (pattern detection + explanation).

Compares the current period with the previous one and explains *why* spending changed:
  * category deltas,
  * driver segments — (subcategory × weekday/weekend-night) cells ranked by their share of the
    change, so "weekend restaurant dinners account for 64% of the increase" is a computed fact,
  * frequency vs. ticket-size decomposition:  Δ = (n₁−n₀)·avg₀  +  n₁·(avg₁−avg₀).
Every number here is computed from the group's transactions.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from ..ml.taxonomy import CATEGORY_COLORS, get_subcategory
from ..services.snapshot import ExpenseInfo, GroupSnapshot, memo


def is_weekend_time(dt: datetime) -> bool:
    """Bangladesh weekend: Friday & Saturday, plus Thursday evening (the start of the weekend)."""
    return dt.weekday() in (4, 5) or (dt.weekday() == 3 and dt.hour >= 17)


def _pct(a: float, b: float) -> float | None:
    return round((a / b - 1) * 100, 1) if b else None


def _segment(e: ExpenseInfo) -> tuple[str, str]:
    return get_subcategory(e.subcategory).label, ("weekend" if is_weekend_time(e.occurred_at) else "weekday")


def spending_report(snap: GroupSnapshot, days: int = 30) -> dict:
    return memo(snap, f"spending:{days}", lambda: _report(snap, days))


def _report(snap: GroupSnapshot, days: int) -> dict:
    now = snap.as_of
    cur_start = now - timedelta(days=days)
    prev_start = now - timedelta(days=2 * days)
    cur = [e for e in snap.expenses if cur_start <= e.occurred_at <= now]
    prev = [e for e in snap.expenses if prev_start <= e.occurred_at < cur_start]
    total_cur = sum(e.amount for e in cur)
    total_prev = sum(e.amount for e in prev)

    by_cat_cur: dict[str, int] = defaultdict(int)
    by_cat_prev: dict[str, int] = defaultdict(int)
    for e in cur:
        by_cat_cur[e.category] += e.amount
    for e in prev:
        by_cat_prev[e.category] += e.amount
    categories = []
    for cat in sorted(set(by_cat_cur) | set(by_cat_prev), key=lambda c: -by_cat_cur.get(c, 0)):
        c, p = by_cat_cur.get(cat, 0), by_cat_prev.get(cat, 0)
        categories.append({"category": cat, "color": CATEGORY_COLORS.get(cat, "#94A3B8"), "current": c, "previous": p,
                           "change": c - p, "change_pct": _pct(c, p),
                           "share_pct": round(c / total_cur * 100, 1) if total_cur else 0.0,
                           "count": sum(1 for e in cur if e.category == cat)})

    one_offs = [e for e in cur if e.is_one_off]
    cur_excl = total_cur - sum(e.amount for e in one_offs)
    prev_excl = total_prev - sum(e.amount for e in prev if e.is_one_off)

    # Driver analysis: the category with the largest change in *recurring behaviour* - unusual
    # one-off expenses are excluded so a single spike can't masquerade as a trend.
    cur_n = [e for e in cur if not e.is_one_off]
    prev_n = [e for e in prev if not e.is_one_off]
    pattern_rows = []
    for cat in {e.category for e in cur_n} | {e.category for e in prev_n}:
        a_ = [e for e in cur_n if e.category == cat]
        b_ = [e for e in prev_n if e.category == cat]
        if len(a_) >= 6 and len(b_) >= 6:
            ca, cb = sum(e.amount for e in a_), sum(e.amount for e in b_)
            pattern_rows.append({"category": cat, "current": ca, "previous": cb, "change": ca - cb,
                                 "change_pct": _pct(ca, cb), "count": len(a_)})
    drivers: list[dict] = []
    focus = max(pattern_rows, key=lambda r: abs(r["change"]), default=None)
    focus_detail = None
    if focus and focus["previous"] and abs(focus["change"]) > 0:
        cat = focus["category"]
        seg_cur: dict[tuple[str, str], list[int]] = defaultdict(list)
        seg_prev: dict[tuple[str, str], list[int]] = defaultdict(list)
        for e in cur_n:
            if e.category == cat:
                seg_cur[_segment(e)].append(e.amount)
        for e in prev_n:
            if e.category == cat:
                seg_prev[_segment(e)].append(e.amount)
        rows = []
        for seg in set(seg_cur) | set(seg_prev):
            a, b = seg_cur.get(seg, []), seg_prev.get(seg, [])
            delta = sum(a) - sum(b)
            rows.append((seg, delta, a, b))
        same_sign = [r for r in rows if (r[1] > 0) == (focus["change"] > 0) and r[1] != 0]
        same_sign.sort(key=lambda r: -abs(r[1]))
        for (label, day_type), delta, a, b in same_sign[:3]:
            n1, n0 = len(a), len(b)
            avg1 = sum(a) / n1 if n1 else 0
            avg0 = sum(b) / n0 if n0 else 0
            freq_effect = (n1 - n0) * avg0
            size_effect = n1 * (avg1 - avg0)
            drivers.append({
                "segment": f"{'Weekend' if day_type == 'weekend' else 'Weekday'} {label.lower()}",
                "subcategory_label": label, "day_type": day_type,
                "current": sum(a), "previous": sum(b), "change": delta,
                "share_of_change_pct": round(delta / focus["change"] * 100, 1),
                "count_current": n1, "count_previous": n0,
                "avg_current": round(avg1), "avg_previous": round(avg0),
                "frequency_effect": round(freq_effect), "ticket_size_effect": round(size_effect),
                "mainly": "frequency" if abs(freq_effect) >= abs(size_effect) else "ticket_size",
            })
        focus_detail = {"category": cat, "change": focus["change"], "change_pct": focus["change_pct"],
                        "current": focus["current"], "previous": focus["previous"], "count": focus["count"],
                        "excludes_unusual": True}

    # Members: paid upfront vs consumed (current period)
    paid: dict[str, int] = defaultdict(int)
    consumed: dict[str, int] = defaultdict(int)
    for e in cur:
        paid[e.payer_id] += e.amount
        for mid, sh in e.shares.items():
            consumed[mid] += sh
    members = [{"member_id": m.id, "name": m.name, "color": m.color, "paid": paid.get(m.id, 0),
                "consumed": consumed.get(m.id, 0),
                "paid_share_pct": round(paid.get(m.id, 0) / total_cur * 100, 1) if total_cur else 0.0}
               for m in snap.members if m.status == "active" or paid.get(m.id) or consumed.get(m.id)]
    members.sort(key=lambda r: -r["paid"])

    # Time patterns (current period)
    weekend_total = sum(e.amount for e in cur if is_weekend_time(e.occurred_at))
    dow_totals = [0] * 7
    for e in cur:
        dow_totals[e.occurred_at.weekday()] += e.amount

    # Daily series (last 90 days) with 7-day moving average
    start = (now - timedelta(days=89)).date()
    daily: dict = defaultdict(int)
    for e in snap.expenses:
        d = e.occurred_at.date()
        if d >= start:
            daily[d] += e.amount
    series = []
    window: list[int] = []
    for i in range(90):
        d = start + timedelta(days=i)
        v = daily.get(d, 0)
        window.append(v)
        if len(window) > 7:
            window.pop(0)
        series.append({"date": d.isoformat(), "total": v, "ma7": round(sum(window) / len(window))})

    # Weekly totals (last 12 weeks)
    weekly = []
    for w in range(11, -1, -1):
        ws = now - timedelta(days=7 * (w + 1))
        we = now - timedelta(days=7 * w)
        weekly.append({"week_start": ws.date().isoformat(),
                       "total": sum(e.amount for e in snap.expenses if ws < e.occurred_at <= we)})

    merchants: dict[str, list[int]] = defaultdict(list)
    for e in cur:
        if e.merchant:
            merchants[e.merchant].append(e.amount)
    top_merchants = sorted(({"merchant": k, "total": sum(v), "count": len(v)} for k, v in merchants.items()),
                           key=lambda r: -r["total"])[:6]

    largest = max(cur, key=lambda e: e.amount, default=None)
    return {
        "period_days": days,
        "period": {"start": cur_start.date().isoformat(), "end": now.date().isoformat()},
        "previous_period": {"start": prev_start.date().isoformat(), "end": cur_start.date().isoformat()},
        "total": total_cur, "previous_total": total_prev, "change": total_cur - total_prev,
        "change_pct": _pct(total_cur, total_prev),
        "change_pct_excluding_unusual": _pct(cur_excl, prev_excl),
        "unusual_in_period": [{"id": e.id, "amount": e.amount, "description": e.description} for e in one_offs],
        "count": len(cur), "previous_count": len(prev),
        "average_expense": round(total_cur / len(cur)) if cur else 0,
        "largest_expense": ({"id": largest.id, "amount": largest.amount, "description": largest.description,
                             "category": largest.category, "date": largest.occurred_at.isoformat()} if largest else None),
        "daily_average": round(total_cur / days),
        "categories": categories,
        "focus": focus_detail,
        "drivers": drivers,
        "members": members,
        "weekend_share_pct": round(weekend_total / total_cur * 100, 1) if total_cur else 0.0,
        "by_weekday": [{"dow": n, "total": t} for n, t in zip(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], dow_totals)],
        "daily_series": series,
        "weekly_series": weekly,
        "top_merchants": top_merchants,
        "basis": f"{len(cur)} transactions in the last {days} days vs {len(prev)} in the {days} days before",
        "method": "Statistical period comparison with driver decomposition (deterministic)",
    }
