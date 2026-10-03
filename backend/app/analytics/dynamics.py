"""AI Feature 6 — Group financial dynamics (observable payment behaviour only).

Measures, per member:
  * share of upfront payments vs. share of consumption (what they actually used),
  * share of high-value expenses (top quartile by amount) they fronted,
  * reimbursement delay — amount-weighted days a negative balance stayed open before being
    cleared (still-open balances count at their current age), computed with a member-level
    FIFO ledger netted per expense, so it works no matter who paid whom,
  * how long the member waited to be reimbursed when they fronted money.

Group level: Contribution Balance Index  CBI = 1 − ½·Σ|paid_shareᵢ − consumed_shareᵢ|  (1 = everyone
fronts money in proportion to what they use).

Deliberately NOT inferred: personality, intent, reliability, income or financial status.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta

import numpy as np

from ..core.money import fmt_taka
from ..services.snapshot import GroupSnapshot, memo

WINDOW_DAYS = 90
RESPONSIBLE_NOTE = ("Only observable payment behaviour is analysed. GroupWise does not infer personality, intent, "
                    "reliability or anyone's financial situation.")


def _fifo_delays(snap: GroupSnapshot, since: datetime) -> dict[str, dict]:
    """Member-level FIFO over net-balance changes → debtor delay and creditor wait (days)."""
    events: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
    for e in snap.expenses:
        # Net per expense: a payer's own share is not a debt they "repay" to themselves.
        deltas: dict[str, int] = defaultdict(int)
        deltas[e.payer_id] += e.amount
        for mid, sh in e.shares.items():
            deltas[mid] -= sh
        for mid, delta in deltas.items():
            if delta:
                events[mid].append((e.occurred_at, delta))
    for s in snap.settlements:
        events[s.from_id].append((s.occurred_at, s.amount))
        events[s.to_id].append((s.occurred_at, -s.amount))

    out: dict[str, dict] = {}
    now = snap.as_of
    for mid, evs in events.items():
        evs.sort(key=lambda x: x[0])
        debt: deque[list] = deque()  # [amount, created_at]
        credit: deque[list] = deque()
        d_num = d_den = c_num = c_den = 0.0
        for when, delta in evs:
            if delta < 0:
                remaining = -delta
                while remaining and credit:  # a negative change first eats the member's credit
                    lot = credit[0]
                    take = min(lot[0], remaining)
                    if when >= since:
                        c_num += take * (when - lot[1]).total_seconds() / 86400
                        c_den += take
                    lot[0] -= take
                    remaining -= take
                    if lot[0] == 0:
                        credit.popleft()
                if remaining:
                    debt.append([remaining, when])
            else:
                remaining = delta
                while remaining and debt:
                    lot = debt[0]
                    take = min(lot[0], remaining)
                    if when >= since:
                        d_num += take * (when - lot[1]).total_seconds() / 86400
                        d_den += take
                    lot[0] -= take
                    remaining -= take
                    if lot[0] == 0:
                        debt.popleft()
                if remaining:
                    credit.append([remaining, when])
        open_debt = sum(l[0] for l in debt)
        oldest = (now - debt[0][1]).days if debt else 0
        # Still-open balances count at their current age (otherwise unpaid debts would look "fast").
        for amount, created in debt:
            if created >= since:
                d_num += amount * (now - created).total_seconds() / 86400
                d_den += amount
        for amount, created in credit:
            if created >= since:
                c_num += amount * (now - created).total_seconds() / 86400
                c_den += amount
        out[mid] = {
            "avg_settle_days": round(d_num / d_den, 1) if d_den else None,
            "settled_amount": int(d_den),
            "avg_wait_days": round(c_num / c_den, 1) if c_den else None,
            "open_debt": int(open_debt),
            "oldest_open_debt_days": oldest,
        }
    return out


def dynamics_report(snap: GroupSnapshot, me_member_id: str | None = None) -> dict:
    base = memo(snap, "dynamics", lambda: _report(snap))
    if me_member_id is None:
        return base
    return {**base, "members": [{**m, "is_you": m["member_id"] == me_member_id} for m in base["members"]]}


def _report(snap: GroupSnapshot) -> dict:
    now = snap.as_of
    since = now - timedelta(days=WINDOW_DAYS)
    window = [e for e in snap.expenses if e.occurred_at >= since]
    if len(window) < 8:
        return {"status": "insufficient_data", "message": "More shared expenses are needed to analyse payment patterns.",
                "responsible_note": RESPONSIBLE_NOTE}
    total = sum(e.amount for e in window)
    amounts = np.array([e.amount for e in window])
    high_cut = float(np.percentile(amounts, 75))
    high = [e for e in window if e.amount >= high_cut]
    high_total = sum(e.amount for e in high) or 1

    paid: dict[str, int] = defaultdict(int)
    paid_n: dict[str, int] = defaultdict(int)
    consumed: dict[str, int] = defaultdict(int)
    high_paid: dict[str, int] = defaultdict(int)
    for e in window:
        paid[e.payer_id] += e.amount
        paid_n[e.payer_id] += 1
        for mid, sh in e.shares.items():
            consumed[mid] += sh
    for e in high:
        high_paid[e.payer_id] += e.amount
    delays = _fifo_delays(snap, since)

    members = []
    for m in snap.members:
        if m.status != "active" and not paid.get(m.id) and not consumed.get(m.id):
            continue
        p_share = paid.get(m.id, 0) / total
        c_share = consumed.get(m.id, 0) / total
        d = delays.get(m.id, {})
        members.append({
            "member_id": m.id, "name": m.name, "color": m.color,
            "paid": paid.get(m.id, 0), "paid_count": paid_n.get(m.id, 0),
            "paid_share_pct": round(p_share * 100, 1),
            "consumed": consumed.get(m.id, 0), "consumed_share_pct": round(c_share * 100, 1),
            "imbalance_pct": round((p_share - c_share) * 100, 1),
            "high_value_paid_share_pct": round(high_paid.get(m.id, 0) / high_total * 100, 1),
            "avg_settle_days": d.get("avg_settle_days"),
            "avg_wait_days": d.get("avg_wait_days"),
            "open_debt": d.get("open_debt", 0),
            "oldest_open_debt_days": d.get("oldest_open_debt_days", 0),
        })
    members.sort(key=lambda r: -r["paid_share_pct"])
    cbi = 1 - 0.5 * sum(abs(r["paid_share_pct"] - r["consumed_share_pct"]) / 100 for r in members)
    settle_vals = [r["avg_settle_days"] for r in members if r["avg_settle_days"] is not None]
    median_settle = float(np.median(settle_vals)) if settle_vals else None

    insights: list[dict] = []
    recs: list[dict] = []
    top = members[0] if members else None
    if top and top["imbalance_pct"] >= 12 and top["paid_share_pct"] >= 1.5 * max(top["consumed_share_pct"], 1):
        under = min(members, key=lambda r: r["imbalance_pct"])
        insights.append({
            "kind": "payer_concentration", "severity": "warning", "member_id": top["member_id"],
            "title": f"{top['name']} is covering most upfront costs",
            "text": f"{top['name']} paid {top['paid_share_pct']:.0f}% of the group's upfront expenses in the last "
                    f"{WINDOW_DAYS} days while accounting for {top['consumed_share_pct']:.0f}% of what the group consumed "
                    f"— including {top['high_value_paid_share_pct']:.0f}% of high-value expenses (≥ {fmt_taka(high_cut)}).",
            "evidence": {"paid_share_pct": top["paid_share_pct"], "consumed_share_pct": top["consumed_share_pct"],
                         "high_value_share_pct": top["high_value_paid_share_pct"], "high_value_threshold": round(high_cut)},
        })
        recs.append({
            "key": "rotate_payer", "title": "Rotate who pays for high-value expenses",
            "text": f"Consider rotating payer responsibility for upcoming high-value expenses. Based on the last "
                    f"{WINDOW_DAYS} days, {under['name']} has fronted the least relative to their share "
                    f"({under['paid_share_pct']:.0f}% paid vs {under['consumed_share_pct']:.0f}% consumed).",
            "suggested_next_payer": {"member_id": under["member_id"], "name": under["name"]},
        })
    if median_settle is not None:
        slow = [r for r in members if r["avg_settle_days"] is not None and r["avg_settle_days"] >= max(5.0, 2 * median_settle)]
        for r in slow[:1]:
            insights.append({
                "kind": "settlement_timing", "severity": "info", "member_id": r["member_id"],
                "title": "Settlement timing varies across the group",
                "text": f"Balances owed by {r['name']} have stayed open {r['avg_settle_days']:.1f} days on average "
                        f"before being cleared, compared with a group median of {median_settle:.1f} days.",
                "evidence": {"avg_settle_days": r["avg_settle_days"], "group_median_days": round(median_settle, 1)},
            })
            recs.append({"key": "weekly_settle_up", "title": "Agree on a weekly settle-up day",
                         "text": "A fixed weekly settle-up keeps balances small and reduces how long anyone waits to be "
                                 "reimbursed."})
    if cbi >= 0.9:
        insights.append({"kind": "balanced", "severity": "positive", "title": "Upfront payments are well balanced",
                         "text": f"Members front money roughly in proportion to what they use "
                                 f"(contribution balance index {cbi:.2f}).", "evidence": {"cbi": round(cbi, 2)}})
    return {
        "status": "ok",
        "window_days": WINDOW_DAYS,
        "basis": f"{len(window)} expenses and {sum(1 for s in snap.settlements if s.occurred_at >= since)} settlements "
                 f"in the last {WINDOW_DAYS} days",
        "total": total,
        "contribution_balance_index": round(cbi, 3),
        "median_settle_days": round(median_settle, 1) if median_settle is not None else None,
        "high_value_threshold": round(high_cut),
        "members": members,
        "insights": insights,
        "recommendations": recs,
        "responsible_note": RESPONSIBLE_NOTE,
        "method": "Deterministic behavioural analytics (shares, FIFO reimbursement ledger, balance index)",
    }
