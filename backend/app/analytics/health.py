"""Group Financial Health — a *prototype* indicator with a fully transparent calculation.

  factor                      weight  scoring (0–100)
  --------------------------  ------  ------------------------------------------------------------
  Spending stability           20%    100 − 100·(CV of weekly spend − 0.15)/0.85, last 12 weeks
  Goal progress                25%    min(projected / target, 1)·100 (average over active goals)
  Settlement timeliness        20%    100 at ≤ 2 days average settle time → 0 at ≥ 14 days
  Unusual spending frequency   15%    100 at 0% unusual expenses → 0 at ≥ 5% (last 90 days)
  Contribution balance         20%    contribution balance index × 100

It is not a credit score and makes no claim of scientific or financial accuracy.
"""
from __future__ import annotations

from datetime import timedelta

import numpy as np

from ..ml.forecast import RECURRING_SUBS
from ..services.snapshot import GroupSnapshot, memo
from .dynamics import dynamics_report
from .goals import plan_goal

DISCLAIMER = ("Prototype financial health indicator. It summarises observable group behaviour with a simple, "
              "transparent formula — it is not a credit score or financial advice.")


def _clip(v: float) -> float:
    return max(0.0, min(100.0, v))


def health_score(snap: GroupSnapshot) -> dict:
    return memo(snap, "health", lambda: _health(snap))


def _health(snap: GroupSnapshot) -> dict:
    now = snap.as_of
    factors: list[dict] = []

    weekly = []
    for w in range(12):
        we = now - timedelta(days=7 * w)
        ws = we - timedelta(days=7)
        weekly.append(sum(e.amount for e in snap.expenses if ws < e.occurred_at <= we and not e.is_one_off
                          and e.subcategory not in RECURRING_SUBS))
    active_weeks = [w for w in weekly if w > 0]
    if len(active_weeks) >= 4:
        arr = np.array(active_weeks, dtype=float)
        cv = float(arr.std() / arr.mean())
        factors.append({"key": "stability", "label": "Spending stability", "weight": 0.20,
                        "score": _clip(100 - 100 * (cv - 0.15) / 0.85), "value": f"weekly variation {cv * 100:.0f}%",
                        "explanation": "Lower week-to-week variation in day-to-day spending scores higher (bills excluded)."})
    else:
        factors.append({"key": "stability", "label": "Spending stability", "weight": 0.20, "score": None,
                        "value": "not enough weekly history", "explanation": "Needs at least 4 active weeks."})

    active_goals = [g for g in snap.goals if g.status == "active"]
    if active_goals:
        ratios = [min(plan_goal(snap, g)["projection"]["on_track_pct"] / 100, 1.0) for g in active_goals]
        avg = float(np.mean(ratios))
        factors.append({"key": "goals", "label": "Goal progress", "weight": 0.25, "score": _clip(avg * 100),
                        "value": f"{avg * 100:.0f}% of target projected",
                        "explanation": "Projected amount at the deadline as a share of the target."})
    else:
        factors.append({"key": "goals", "label": "Goal progress", "weight": 0.25, "score": None,
                        "value": "no active goal", "explanation": "Create a shared goal to include this factor."})

    dyn = dynamics_report(snap)
    if dyn.get("status") == "ok" and dyn.get("median_settle_days") is not None:
        vals = [m["avg_settle_days"] for m in dyn["members"] if m["avg_settle_days"] is not None]
        avg_days = float(np.mean(vals))
        factors.append({"key": "settlement", "label": "Settlement timeliness", "weight": 0.20,
                        "score": _clip(100 - (avg_days - 2) / 12 * 100), "value": f"{avg_days:.1f} days on average",
                        "explanation": "How quickly balances are cleared after an expense."})
        factors.append({"key": "balance", "label": "Contribution balance", "weight": 0.20,
                        "score": _clip(dyn["contribution_balance_index"] * 100),
                        "value": f"index {dyn['contribution_balance_index']:.2f}",
                        "explanation": "Whether members front money in proportion to what they use."})
    else:
        factors.append({"key": "settlement", "label": "Settlement timeliness", "weight": 0.20, "score": None,
                        "value": "not enough settlements", "explanation": "Record settlements to include this factor."})
        factors.append({"key": "balance", "label": "Contribution balance", "weight": 0.20, "score": None,
                        "value": "not enough expenses", "explanation": "Needs more shared expenses."})

    since = now - timedelta(days=90)
    recent = [e for e in snap.expenses if e.occurred_at >= since]
    if len(recent) >= 10:
        rate = sum(1 for e in recent if (e.anomaly_score or 0) >= 0.6) / len(recent)
        factors.append({"key": "unusual", "label": "Unusual spending frequency", "weight": 0.15,
                        "score": _clip(100 - rate / 0.05 * 100), "value": f"{rate * 100:.1f}% of expenses flagged",
                        "explanation": "Share of recent expenses the anomaly model flagged as unusual."})
    else:
        factors.append({"key": "unusual", "label": "Unusual spending frequency", "weight": 0.15, "score": None,
                        "value": "not enough expenses", "explanation": "Needs at least 10 recent expenses."})

    scored = [f for f in factors if f["score"] is not None]
    if len(scored) < 2:
        return {"status": "insufficient_data", "factors": factors, "disclaimer": DISCLAIMER,
                "message": "More history is needed to compute a health indicator."}
    weight_sum = sum(f["weight"] for f in scored)
    score = sum(f["score"] * f["weight"] for f in scored) / weight_sum
    for f in factors:
        if f["score"] is not None:
            f["score"] = round(f["score"])
            f["contribution"] = round(f["score"] * f["weight"] / weight_sum, 1)
    band = "strong" if score >= 80 else ("good" if score >= 65 else ("fair" if score >= 50 else "needs attention"))
    weakest = min(scored, key=lambda f: f["score"])
    return {
        "status": "ok", "score": round(score), "band": band, "factors": factors,
        "weakest_factor": weakest["key"],
        "formula": "Weighted average of the available factors (weights re-normalised when a factor is missing).",
        "disclaimer": DISCLAIMER,
    }
