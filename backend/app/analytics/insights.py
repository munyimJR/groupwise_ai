"""Insight feed + recommendation engine.

Turns the outputs of every analysis into explainable cards with the same structure:
  observation (fact) → inference (what the model/analysis concluded) → why (evidence)
  → action (recommendation) → expected outcome (simulated)  + method & confidence labels.

Recommendations are a rule + simulation hybrid: candidates are generated from the analyses,
their impact is computed with the What-If engine, and they are ranked by priority and impact.
People decide — dismissed recommendations are not shown again for a week.
"""
from __future__ import annotations

import math
from datetime import timedelta

from ..core.money import fmt_taka
from ..ml.taxonomy import DISCRETIONARY_CATEGORIES
from ..services.snapshot import GroupSnapshot
from .dynamics import dynamics_report
from .forecasting import group_forecast
from .goals import plan_goal
from .ledger import balances
from .spending import spending_report
from .whatif import simulate


def _likely(v: float) -> str:
    return "<1%" if v < 1 else (">99%" if v > 99 else f"{v:.0f}%")


def _confidence_from_n(n: int) -> dict:
    if n >= 40:
        return {"level": "high", "value": 0.85, "basis": f"{n} transactions"}
    if n >= 15:
        return {"level": "medium", "value": 0.65, "basis": f"{n} transactions"}
    return {"level": "low", "value": 0.4, "basis": f"only {n} transactions"}


def build_insights(snap: GroupSnapshot, me_member_id: str | None = None) -> list[dict]:
    insights: list[dict] = []
    gid = snap.group_id

    # 1) Spending trend
    rep = spending_report(snap, 30)
    focus = rep.get("focus")
    if focus and focus["change_pct"] is not None and abs(focus["change_pct"]) >= 10 and abs(focus["change"]) >= 100000:
        cat = focus["category"]
        cat_row = focus
        up = focus["change"] > 0
        why = [f"{cat}: {fmt_taka(cat_row['current'])} in the last 30 days vs {fmt_taka(cat_row['previous'])} in the "
               f"previous 30 days ({cat_row['count']} expenses, unusual one-offs excluded)"]
        inference = None
        if rep["drivers"]:
            d = rep["drivers"][0]
            share = d["share_of_change_pct"]
            inference = f"{d['segment'].capitalize()} expenses account for {min(share, 100):.0f}% of the {'increase' if up else 'decrease'}."
            if d["mainly"] == "frequency":
                why.append(f"{d['segment'].capitalize()}: {d['count_previous']} → {d['count_current']} expenses — the change "
                           f"comes mostly from how often, not how much (avg {fmt_taka(d['avg_previous'])} → "
                           f"{fmt_taka(d['avg_current'])})")
            else:
                why.append(f"{d['segment'].capitalize()}: average bill {fmt_taka(d['avg_previous'])} → "
                           f"{fmt_taka(d['avg_current'])} — the change comes mostly from bigger bills")
        if rep["unusual_in_period"] and rep["change_pct"] is not None:
            why.append(f"Total group spending changed {rep['change_pct']:+.0f}% including "
                       f"{len(rep['unusual_in_period'])} unusual expense(s), "
                       f"{rep['change_pct_excluding_unusual']:+.0f}% without them")
        action = None
        if up and cat in DISCRETIONARY_CATEGORIES:
            action = {"text": f"Try a What-If: reduce {cat} by 15% and see the effect on your goal.",
                      "link": f"/g/{gid}/what-if?cat={cat}&pct=-15"}
        insights.append({
            "id": f"trend:{cat}", "kind": "spending_trend", "severity": "warning" if up else "positive",
            "title": f"{cat} spending {'increased' if up else 'decreased'} {abs(focus['change_pct']):.0f}%",
            "observation": why[0], "inference": inference, "why": why[1:], "action": action,
            "confidence": _confidence_from_n(rep["count"] + rep["previous_count"]),
            "method": "Statistical pattern detection (period comparison + driver decomposition)",
            "evidence": {"category": cat, "change_pct": focus["change_pct"], "current": cat_row["current"],
                         "previous": cat_row["previous"]},
        })

    # 1b) Inactive group with open balances (e.g. a finished trip)
    last = max((e.occurred_at for e in snap.expenses), default=None)
    if last is not None and (snap.as_of - last).days > 21:
        bal = balances(snap)
        if bal["simplified_transfer_count"]:
            insights.append({
                "id": "inactive:open_balances", "kind": "settlement", "severity": "warning",
                "title": f"{fmt_taka(bal['outstanding_total'])} still unsettled",
                "observation": f"No new expenses for {(snap.as_of - last).days} days - total spent "
                               f"{fmt_taka(bal['total_spent'])}.",
                "inference": f"{bal['simplified_transfer_count']} payments would settle everyone "
                             f"(instead of {bal['naive_transfer_count']} pairwise payments).",
                "why": ["Debt simplification is a deterministic algorithm (minimum cash-flow), not AI."],
                "action": {"text": "Open the settle-up plan.", "link": f"/g/{gid}/balances"},
                "confidence": {"level": "high", "value": 1.0, "basis": "exact ledger calculation"},
                "method": "Deterministic balance engine",
                "evidence": {"outstanding": bal["outstanding_total"], "transfers": bal["simplified_transfer_count"]},
            })

    # 2) Unusual expenses awaiting review
    flagged = sorted((e for e in snap.expenses if e.anomaly_status == "flagged"), key=lambda e: e.occurred_at, reverse=True)
    for e in flagged[:2]:
        reasons = [r["text"] for r in (e.anomaly_reasons or [])]
        insights.append({
            "id": f"anomaly:{e.id}", "kind": "anomaly", "severity": "alert",
            "title": f"Unusual {fmt_taka(e.amount)} expense detected",
            "observation": f"“{e.description}” paid by {snap.member_name(e.payer_id)} on "
                           f"{e.occurred_at.strftime('%a %d %b, %I:%M %p')}",
            "inference": f"Anomaly score {round((e.anomaly_score or 0) * 100)}% — this looks different from the group's "
                         f"usual spending.",
            "why": reasons[:3],
            "action": {"text": "Review it: mark as valid, or edit it if it was entered by mistake. Nothing is blocked.",
                       "link": f"/g/{gid}/transactions/{e.id}"},
            "confidence": {"level": "high" if (e.anomaly_score or 0) >= 0.8 else "medium",
                           "value": round(e.anomaly_score or 0, 2), "basis": "anomaly score"},
            "method": "ML: Isolation Forest + robust statistics + rules",
            "evidence": {"expense_id": e.id, "amount": e.amount, "score": e.anomaly_score},
        })

    # 3) Forecast
    fc = group_forecast(snap, 7)
    if fc.get("status") == "ok":
        last = fc["comparison"]["last_period_actual"]
        pressure_days = [p["dow"] for p in fc["pressure_days"]]
        why = [d["text"] for d in fc["drivers"][:3]]
        insights.append({
            "id": "forecast:7", "kind": "forecast", "severity": "warning" if pressure_days else "info",
            "title": f"Next 7 days: about {fmt_taka(fc['total'])} projected",
            "observation": f"The group spent {fmt_taka(last)} in the last 7 days.",
            "inference": (f"Highest pressure expected on {', '.join(pressure_days)}." if pressure_days else
                          "No unusually heavy days expected."),
            "why": why,
            "action": {"text": "Open the forecast to see the daily breakdown and each member's expected share.",
                       "link": f"/g/{gid}/forecast"},
            "confidence": {"level": fc["confidence"], "value": {"high": 0.8, "medium": 0.6, "low": 0.4}[fc["confidence"]],
                           "basis": f"80% range {fmt_taka(fc['interval']['low'])}–{fmt_taka(fc['interval']['high'])}"},
            "method": "Forecast model: recurring bills + seasonal exponential smoothing",
            "evidence": {"total": fc["total"], "interval": fc["interval"], "pressure_days": pressure_days},
        })

    # 4) Goals
    for g in snap.goals:
        if g.status != "active":
            continue
        plan = plan_goal(snap, g)
        p = plan["projection"]
        if plan["status"] in ("not_started", "deadline_passed"):
            continue
        good = plan["status"] in ("on_track", "achieved")
        top = plan["scenarios"][0] if plan["scenarios"] else None
        insights.append({
            "id": f"goal:{g.id}", "kind": "goal", "severity": "positive" if good else "warning",
            "title": f"{g.title} is {min(p['on_track_pct'], 999):.0f}% on track",
            "observation": f"{fmt_taka(plan['saved'])} saved of {fmt_taka(plan['target'])} "
                           f"({plan['progress_pct']:.0f}%), {plan['days_left']} days left.",
            "inference": plan["explanation"],
            "why": [f"Contribution rate: {fmt_taka(p['rate_monthly'])}/month; needed: {fmt_taka(p['required_monthly'])}/month",
                    f"Simulated likelihood of reaching the target: {_likely(p['likelihood_pct'])} "
                    f"({p['simulations']:,} simulated futures)"],
            "action": {"text": top["text"], "link": f"/g/{gid}/goals/{g.id}"} if top else None,
            "confidence": {"level": "medium", "value": 0.6, "basis": f"{len(g.contributions)} contributions"},
            "method": "Projection + Monte-Carlo simulation",
            "evidence": {"goal_id": g.id, "on_track_pct": p["on_track_pct"], "gap": p["gap"]},
        })

    # 5) Dynamics
    dyn = dynamics_report(snap)
    if dyn.get("status") == "ok":
        for ins in dyn["insights"][:1]:
            rec = next((r for r in dyn["recommendations"]), None)
            insights.append({
                "id": f"dynamics:{ins['kind']}", "kind": "dynamics", "severity": ins["severity"],
                "title": ins["title"], "observation": ins["text"], "inference": None, "why": [dyn["basis"]],
                "action": {"text": rec["text"], "link": f"/g/{gid}/dynamics"} if rec else None,
                "confidence": _confidence_from_n(len([e for e in snap.expenses if e.occurred_at >= snap.as_of - timedelta(days=90)])),
                "method": "Behavioural analytics on observable payments only",
                "evidence": ins.get("evidence", {}),
            })
    return insights


def build_recommendations(snap: GroupSnapshot, dismissed: set[str] | None = None, me_member_id: str | None = None) -> list[dict]:
    dismissed = dismissed or set()
    recs: list[dict] = []
    gid = snap.group_id
    rep = spending_report(snap, 30)

    for g in snap.goals:
        if g.status != "active":
            continue
        plan = plan_goal(snap, g)
        dining = next((s for s in plan["scenarios"] if s["key"] == "reduce_dining"), None)
        if dining and plan["projection"]["gap"] > 0:
            pct = min(40, max(5, math.ceil(dining["reduction_pct"] / 5) * 5))
            sim = simulate(snap, {"Food": -pct}, goal_id=g.id, me_member_id=me_member_id)
            weekend_up = any(d["day_type"] == "weekend" and d["change"] > 0 for d in rep.get("drivers", []))
            what = "weekend dining" if weekend_up else "discretionary dining"
            if sim.get("goal"):
                b, s = sim["goal"]["baseline"], sim["goal"]["scenario"]
                recs.append({
                    "key": f"reduce_dining:{g.id}", "priority": 1, "kind": "goal",
                    "title": f"Reduce {what} to protect “{g.title}”",
                    "text": f"Reducing {what} expenses by about {pct}% (≈{fmt_taka(sim['monthly_savings'])}/month) could help "
                            f"keep the {g.title} goal on track.",
                    "expected_outcome": f"Projected goal progress {b['on_track_pct']:.0f}% → {s['on_track_pct']:.0f}%; "
                                        f"simulated likelihood {_likely(b['likelihood_pct'])} → "
                                        f"{_likely(s['likelihood_pct'])}.",
                    "impact": {"monthly_savings": sim["monthly_savings"], "on_track_before": b["on_track_pct"],
                               "on_track_after": s["on_track_pct"], "likelihood_before": b["likelihood_pct"],
                               "likelihood_after": s["likelihood_pct"]},
                    "assumption": sim["assumption"],
                    "link": f"/g/{gid}/what-if?cat=Food&pct=-{pct}&goal={g.id}",
                })

    flagged = [e for e in snap.expenses if e.anomaly_status == "flagged"]
    if flagged:
        e = max(flagged, key=lambda x: x.occurred_at)
        recs.append({
            "key": f"review_anomaly:{e.id}", "priority": 2, "kind": "anomaly",
            "title": f"Review the unusual {fmt_taka(e.amount)} expense",
            "text": f"“{e.description}” is unusual for this group. Confirm it's correct before anyone settles up.",
            "expected_outcome": "Prevents a data-entry mistake from flowing into everyone's balances.",
            "link": f"/g/{gid}/transactions/{e.id}",
        })

    dyn = dynamics_report(snap)
    if dyn.get("status") == "ok":
        for r in dyn["recommendations"][:1]:
            recs.append({"key": r["key"], "priority": 3, "kind": "dynamics", "title": r["title"], "text": r["text"],
                         "expected_outcome": "A more even spread of upfront payments and shorter reimbursement waits.",
                         "link": f"/g/{gid}/dynamics"})

    bal = balances(snap)
    if bal["simplified_transfer_count"] > 0 and bal["outstanding_total"] >= 100000:
        recs.append({
            "key": "settle_up", "priority": 4, "kind": "settlement",
            "title": f"Settle up with {bal['simplified_transfer_count']} payment{'s' if bal['simplified_transfer_count'] != 1 else ''}",
            "text": f"{fmt_taka(bal['outstanding_total'])} is outstanding. Simplified, "
                    f"{bal['simplified_transfer_count']} payment(s) clear every balance "
                    f"(instead of {bal['naive_transfer_count']} pairwise payments).",
            "expected_outcome": "Everyone back to zero; nobody waiting to be reimbursed.",
            "link": f"/g/{gid}/balances",
        })

    fc = group_forecast(snap, 7)
    if fc.get("status") == "ok" and fc["pressure_days"]:
        days = ", ".join(p["dow"] for p in fc["pressure_days"])
        recs.append({
            "key": "pressure_budget", "priority": 5, "kind": "forecast",
            "title": f"Plan ahead for {days}",
            "text": f"Spending is projected to peak on {days}. Agreeing a shared budget for those days in advance "
                    f"helps avoid surprises.",
            "expected_outcome": f"Next-7-day projection: {fmt_taka(fc['total'])}.",
            "link": f"/g/{gid}/forecast",
        })

    for r in recs:
        r.setdefault("method", "Rule-based candidate + What-If simulation of impact")
        r["label"] = "recommendation"
    recs = [r for r in recs if r["key"] not in dismissed]
    recs.sort(key=lambda r: r["priority"])
    return recs
