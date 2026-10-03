"""Signature feature — What-If simulator.

Baseline = next-30-day forecast by category (falls back to the last 60 days' average when the
group has too little history to forecast). A scenario applies per-category % changes, an overall
% change and optional extra contributions, then recomputes:
  monthly spending, savings, per-member burden, next-7-day pressure, and — for a selected goal —
  projected amount at the deadline, completion date, remaining gap and simulated likelihood.

Explicit assumption (shown to the user): the group's total outflow stays fixed, so money saved on
spending is redirected to the goal, and extra spending comes out of goal contributions.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from ..core.money import fmt_taka
from ..services.snapshot import GroupSnapshot
from .forecasting import consumption_shares, group_forecast
from .goals import WEEKS_PER_MONTH, discretionary_monthly, plan_goal, simulate_final

ASSUMPTION = ("Assumes the group's total outflow stays the same: money saved on spending is redirected to the goal, "
              "and extra spending reduces goal contributions.")


def baseline_monthly(snap: GroupSnapshot) -> tuple[dict[str, float], str]:
    fc = group_forecast(snap, 30)
    if fc.get("status") == "ok":
        return {r["category"]: float(r["total"]) for r in fc["by_category"]}, "30-day forecast"
    since = snap.as_of - timedelta(days=60)
    by_cat: dict[str, float] = defaultdict(float)
    for e in snap.expenses:
        if e.occurred_at >= since and not e.is_one_off:
            by_cat[e.category] += e.amount * 30.44 / 60
    return dict(by_cat), "average of the last 60 days"


def simulate(snap: GroupSnapshot, category_changes: dict[str, float], overall_change_pct: float = 0.0,
             extra_monthly_contribution: float = 0.0, goal_id: str | None = None, redirect_savings: bool = True,
             me_member_id: str | None = None) -> dict:
    base, basis = baseline_monthly(snap)
    if not base:
        return {"status": "insufficient_data", "message": "Add some shared expenses first — the simulator projects from "
                                                           "your group's real spending."}
    overall = 1 + overall_change_pct / 100
    rows = []
    for cat, amount in sorted(base.items(), key=lambda kv: -kv[1]):
        pct = category_changes.get(cat, 0.0)
        new = amount * (1 + pct / 100) * overall
        rows.append({"category": cat, "baseline": round(amount), "scenario": round(new), "change": round(new - amount),
                     "change_pct": round((new / amount - 1) * 100, 1) if amount else 0.0})
    base_total = sum(base.values())
    scen_total = sum(r["scenario"] for r in rows)
    savings = base_total - scen_total  # >0 means the scenario spends less

    shares = consumption_shares(snap)
    member_rows = sorted(({"member_id": mid, "name": snap.member_name(mid), "baseline": round(base_total * s),
                           "scenario": round(scen_total * s), "is_you": mid == me_member_id}
                          for mid, s in shares.items()), key=lambda r: -r["scenario"])

    # Pressure: next 7 days under the scenario vs. the group's recent weekly average
    fc7 = group_forecast(snap, 7)
    pressure = None
    if fc7.get("status") == "ok":
        mult = scen_total / base_total if base_total else 1.0
        next7 = fc7["total"] * mult
        recent_weekly = fc7["comparison"]["avg_daily_8w"] * 7
        ratio = next7 / recent_weekly if recent_weekly else 1.0
        level = "high" if ratio > 1.15 else ("moderate" if ratio > 0.95 else "low")
        pressure = {"next_7_days": round(next7), "recent_weekly_avg": round(recent_weekly), "ratio": round(ratio, 2),
                    "level": level, "pressure_days": [p["dow"] for p in fc7["pressure_days"]]}

    goal_result = None
    goal = next((g for g in snap.goals if g.id == goal_id), None) if goal_id else None
    if goal is None and not goal_id:
        goal = next((g for g in snap.goals if g.status == "active"), None)
    if goal is not None:
        plan = plan_goal(snap, goal)
        p = plan["projection"]
        weeks_left = plan["weeks_left"]
        redirected = savings if redirect_savings else 0.0
        delta_monthly = extra_monthly_contribution + redirected
        new_rate_weekly = max(p["rate_weekly"] + delta_monthly / WEEKS_PER_MONTH, 0.0)
        new_projected = goal.saved + new_rate_weekly * weeks_left
        new_gap = goal.target - new_projected
        today = snap.as_of.date()
        completion = None
        if new_rate_weekly > 0 and goal.saved < goal.target:
            completion = today + timedelta(days=round((goal.target - goal.saved) / new_rate_weekly * 7))
        sims = simulate_final(goal, today, extra_weekly=delta_monthly / WEEKS_PER_MONTH)
        likelihood = float((sims >= goal.target).mean())
        goal_result = {
            "goal_id": goal.id, "title": goal.title, "target": goal.target, "saved": goal.saved,
            "deadline": goal.deadline.isoformat(),
            "baseline": {"projected": p["projected_amount"], "on_track_pct": p["on_track_pct"], "gap": p["gap"],
                         "likelihood_pct": p["likelihood_pct"], "completion_date": p["completion_date_at_current_rate"]},
            "scenario": {"projected": round(new_projected), "on_track_pct": round(new_projected / goal.target * 100, 1),
                         "gap": round(new_gap), "likelihood_pct": round(likelihood * 100, 1),
                         "completion_date": completion.isoformat() if completion else None,
                         "monthly_to_goal": round(new_rate_weekly * WEEKS_PER_MONTH)},
        }

    # Recommended adjustment if the scenario still leaves a gap
    recommendation = None
    disc = discretionary_monthly(snap)
    if goal_result and goal_result["scenario"]["gap"] > 0 and goal_result["baseline"]["gap"] > 0:
        weeks_left = max((goal.deadline - snap.as_of.date()).days / 7, 0.1)
        extra_needed_monthly = goal_result["scenario"]["gap"] / weeks_left * WEEKS_PER_MONTH
        food_now = next((r["scenario"] for r in rows if r["category"] == "Food"), 0)
        if disc["dining"] and food_now:
            more_pct = extra_needed_monthly / food_now * 100
            recommendation = (f"Still {fmt_taka(goal_result['scenario']['gap'])} short. An additional ≈{fmt_taka(extra_needed_monthly)}/month "
                              f"— e.g. a further {more_pct:.0f}% reduction in Food — would close the gap.")
        else:
            recommendation = f"Still short — about {fmt_taka(extra_needed_monthly)}/month more would close the gap."
    elif pressure and pressure["level"] == "high":
        recommendation = ("Spending pressure is high under this scenario — consider agreeing a budget for "
                          f"{', '.join(pressure['pressure_days']) or 'the coming week'} before it starts.")
    elif goal_result and goal_result["scenario"]["gap"] <= 0:
        recommendation = "This scenario is projected to reach the goal on time."

    return {
        "status": "ok",
        "basis": basis,
        "baseline_total": round(base_total), "scenario_total": round(scen_total),
        "monthly_savings": round(savings),
        "categories": rows,
        "members": member_rows,
        "pressure": pressure,
        "goal": goal_result,
        "recommendation": recommendation,
        "assumption": ASSUMPTION,
        "inputs": {"category_changes": category_changes, "overall_change_pct": overall_change_pct,
                   "extra_monthly_contribution": extra_monthly_contribution, "redirect_savings": redirect_savings},
        "method": "Deterministic simulation on top of the forecast model; goal likelihood via bootstrap Monte-Carlo",
        "labels": {"baseline": "projection", "scenario": "simulation", "assumption": "assumption"},
    }
