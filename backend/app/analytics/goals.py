"""AI Feature 5 — Group financial goal planner.

  saved            = Σ contributions so far                                   (fact)
  weekly rate      = saved / weeks elapsed since the goal started             (fact)
  projected        = saved + weekly rate × weeks remaining                    (projection)
  likelihood       = Monte-Carlo: 4,000 futures, each remaining week's total
                     bootstrapped from the group's own weekly contributions   (simulation)
  scenarios        = what closes the gap: redirecting part of discretionary
                     spending, extra contributions per member, or a later deadline

Everything is labelled as estimated/projected/simulated — never a guarantee.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta

import numpy as np

from ..core.money import fmt_taka
from ..ml.taxonomy import get_subcategory
from ..services.snapshot import GoalInfo, GroupSnapshot, memo

N_SIMULATIONS = 4000
WEEKS_PER_MONTH = 30.44 / 7


def discretionary_monthly(snap: GroupSnapshot, days: int = 60) -> dict:
    """Average monthly discretionary spend (by category), from the last `days` days."""
    since = snap.as_of - timedelta(days=days)
    by_cat: dict[str, int] = defaultdict(int)
    dining = 0
    for e in snap.expenses:
        if e.occurred_at >= since and not e.is_one_off and get_subcategory(e.subcategory).discretionary:
            by_cat[e.category] += e.amount
            if e.category == "Food":
                dining += e.amount
    factor = 30.44 / days
    return {"total": round(sum(by_cat.values()) * factor), "dining": round(dining * factor),
            "by_category": {k: round(v * factor) for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1])}}


def weekly_contributions(goal: GoalInfo, as_of: date) -> list[int]:
    weeks = max(1, math.ceil(((as_of - goal.start_date).days + 1) / 7))
    totals = [0] * weeks
    for c in goal.contributions:
        idx = (c.occurred_at.date() - goal.start_date).days // 7
        if 0 <= idx < weeks:
            totals[idx] += c.amount
    return totals


def simulate_final(goal: GoalInfo, as_of: date, extra_weekly: float = 0.0, seed: int = 7) -> np.ndarray:
    weeks_left = max(0.0, (goal.deadline - as_of).days / 7)
    hist = np.array(weekly_contributions(goal, as_of)[:-1] or weekly_contributions(goal, as_of), dtype=float)
    if weeks_left <= 0 or hist.size == 0:
        return np.full(N_SIMULATIONS, float(goal.saved))
    rng = np.random.default_rng(seed)
    full = int(math.floor(weeks_left))
    frac = weeks_left - full
    draws = rng.choice(hist, size=(N_SIMULATIONS, full + 1), replace=True)
    draws[:, -1] *= frac
    return goal.saved + draws.sum(axis=1) + extra_weekly * weeks_left


def plan_goal(snap: GroupSnapshot, goal: GoalInfo) -> dict:
    return memo(snap, f"goal:{goal.id}", lambda: _plan(snap, goal))


def _plan(snap: GroupSnapshot, goal: GoalInfo) -> dict:
    today = snap.as_of.date()
    saved = goal.saved
    remaining_amount = max(goal.target - saved, 0)
    elapsed_days = max((today - goal.start_date).days, 1)
    days_left = (goal.deadline - today).days
    weeks_elapsed = max(elapsed_days / 7, 1.0)
    weeks_left = max(days_left / 7, 0.0)
    rate_weekly = saved / weeks_elapsed
    weekly = weekly_contributions(goal, today)
    recent = weekly[-5:-1] if len(weekly) > 4 else weekly
    recent_rate = sum(recent) / len(recent) if recent else 0
    projected = saved + rate_weekly * weeks_left
    progress_pct = saved / goal.target * 100 if goal.target else 0
    on_track_pct = projected / goal.target * 100 if goal.target else 0
    gap = goal.target - projected
    required_weekly = remaining_amount / weeks_left if weeks_left > 0 else float(remaining_amount)
    required_monthly = required_weekly * WEEKS_PER_MONTH
    rate_monthly = rate_weekly * WEEKS_PER_MONTH
    gap_monthly = max(required_monthly - rate_monthly, 0)

    if saved >= goal.target:
        status = "achieved"
    elif days_left < 0:
        status = "deadline_passed"
    elif not goal.contributions:
        status = "not_started"
    elif on_track_pct >= 100:
        status = "on_track"
    elif on_track_pct >= 85:
        status = "at_risk"
    else:
        status = "off_track"

    sims = simulate_final(goal, today)
    likelihood = float((sims >= goal.target).mean()) if goal.target else 1.0
    p10, p50, p90 = (float(np.percentile(sims, q)) for q in (10, 50, 90))

    completion_date = None
    if rate_weekly > 0 and saved < goal.target:
        completion_date = today + timedelta(days=round((goal.target - saved) / rate_weekly * 7))

    by_member: dict[str, int] = defaultdict(int)
    for c in goal.contributions:
        by_member[c.member_id] += c.amount
    contributors = sorted(({"member_id": mid, "name": snap.member_name(mid), "amount": amt,
                            "share_pct": round(amt / saved * 100, 1) if saved else 0} for mid, amt in by_member.items()),
                          key=lambda r: -r["amount"])
    n_active = max(len(snap.active_members), 1)

    scenarios: list[dict] = []
    disc = discretionary_monthly(snap)
    if gap > 0 and weeks_left > 0 and status not in ("achieved", "deadline_passed"):
        if disc["dining"] > 0:
            cut_pct = gap_monthly / disc["dining"] * 100
            if cut_pct <= 45:
                scenarios.append({
                    "key": "reduce_dining", "label": "Redirect part of discretionary dining",
                    "monthly_change": round(gap_monthly),
                    "text": f"Reducing discretionary dining by about {fmt_taka(gap_monthly)}/month (≈{cut_pct:.0f}% of the "
                            f"current {fmt_taka(disc['dining'])}/month) and moving it to the goal would close the "
                            f"projected gap.",
                    "assumption": "Assumes the money not spent on dining is contributed to the goal.",
                    "reduction_pct": round(cut_pct, 1), "category": "Food",
                })
        per_member_weekly = (required_weekly - rate_weekly) / n_active
        scenarios.append({
            "key": "increase_contributions", "label": "Increase weekly contributions",
            "weekly_change": round(per_member_weekly * n_active),
            "text": f"Each of the {n_active} members adding about {fmt_taka(per_member_weekly)}/week "
                    f"({fmt_taka(per_member_weekly * WEEKS_PER_MONTH)}/month) closes the gap by the deadline.",
            "per_member_weekly": round(per_member_weekly),
        })
        if rate_weekly > 0 and completion_date:
            scenarios.append({
                "key": "extend_deadline", "label": "Move the deadline",
                "text": f"At the current pace the target is projected around {completion_date.strftime('%d %b %Y')} — "
                        f"{(completion_date - goal.deadline).days} days after the current deadline.",
                "new_deadline": completion_date.isoformat(),
            })

    explanation = (f"At the current contribution rate ({fmt_taka(rate_monthly)}/month), the group is projected to reach "
                   f"{fmt_taka(projected)} by {goal.deadline.strftime('%d %b %Y')}"
                   + (f", approximately {fmt_taka(gap)} below the target." if gap > 0 else
                      f", about {fmt_taka(-gap)} above the target."))
    return {
        "goal_id": goal.id, "title": goal.title, "description": goal.description,
        "target": goal.target, "saved": saved, "remaining": remaining_amount,
        "start_date": goal.start_date.isoformat(), "deadline": goal.deadline.isoformat(),
        "days_left": days_left, "weeks_left": round(weeks_left, 1),
        "progress_pct": round(progress_pct, 1),
        "status": status,
        "projection": {
            "projected_amount": round(projected), "on_track_pct": round(on_track_pct, 1), "gap": round(gap),
            "rate_weekly": round(rate_weekly), "rate_monthly": round(rate_monthly), "recent_rate_weekly": round(recent_rate),
            "required_weekly": round(required_weekly), "required_monthly": round(required_monthly),
            "gap_monthly": round(gap_monthly),
            "completion_date_at_current_rate": completion_date.isoformat() if completion_date else None,
            "likelihood_pct": round(likelihood * 100, 1),
            "simulated_range": {"p10": round(p10), "p50": round(p50), "p90": round(p90)},
            "simulations": N_SIMULATIONS,
        },
        "weekly_history": [{"week": i + 1, "start": (goal.start_date + timedelta(days=7 * i)).isoformat(), "amount": v}
                           for i, v in enumerate(weekly)],
        "contributors": contributors,
        "discretionary": disc,
        "scenarios": scenarios,
        "explanation": explanation,
        "labels": {"saved": "fact", "projection": "projection (based on current behaviour)",
                   "likelihood": "simulation", "scenarios": "recommendation"},
        "method": "Linear projection of the observed contribution rate + bootstrap Monte-Carlo simulation",
    }
