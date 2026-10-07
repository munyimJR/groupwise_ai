"""Controlled pilot experiment report: treatment (full GroupWise) vs control (ledger + wallet, no AI layer).

    python -m scripts.experiment_report                 # print
    python -m scripts.experiment_report --out ../research/results

Outcomes are pre-registered in research/experiment/EXPERIMENT_PLAN.md. Each is computed per group, then the arms
are compared as treatment − control with a 95% bootstrap interval over groups (groups are the randomization
unit). Only real accounts in randomized groups are included. Aggregates only, no names or descriptions.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import func, select

from app.analytics.dynamics import dynamics_report
from app.analytics.goals import plan_goal
from app.analytics.ledger import balances
from app.config import get_settings, utc_now
from app.db import SessionLocal
from app.models import (
    ActivityDay,
    Expense,
    ExperimentAssignment,
    Group,
    PaymentRequest,
    RecommendationAction,
    WalletImportItem,
)
from app.services.snapshot import load_snapshot_uncached

OUTCOMES = [
    ("median_days_to_settle", "Median days to settle a debt", "lower"),
    ("unsettled_share", "Share of spending still unsettled", "lower"),
    ("goal_on_track", "Active goals on track or reached", "higher"),
    ("recommendation_acceptance", "Recommendations accepted (of acted on)", "higher"),
    ("week2_retention", "Members active again 7–13 days after first use", "higher"),
    ("wallet_txns_per_week", "Wallet transactions per group per week", "higher"),
    ("wallet_taka_per_week", "Wallet volume per group per week (৳)", "higher"),
    ("expenses_per_week", "Expenses logged per group per week", "higher"),
]
RNG = np.random.default_rng(11)


def _group_metrics(db, g: Group) -> dict:
    snap = load_snapshot_uncached(db, g)
    weeks = max((utc_now() - g.created_at) / timedelta(days=7), 1.0)
    dyn = dynamics_report(snap)
    bal = balances(snap)
    goals = [plan_goal(snap, x) for x in snap.goals if x.status in ("active", "achieved")]
    recs = dict(db.execute(select(RecommendationAction.action, func.count()).where(RecommendationAction.group_id == g.id)
                           .group_by(RecommendationAction.action)).all())
    paid = db.execute(select(func.count(), func.coalesce(func.sum(PaymentRequest.amount_paisa), 0))
                      .where(PaymentRequest.group_id == g.id, PaymentRequest.status == "paid")).one()
    imported = db.scalar(select(func.count()).select_from(WalletImportItem).where(WalletImportItem.group_id == g.id))
    n_exp = db.scalar(select(func.count()).select_from(Expense).where(Expense.group_id == g.id, Expense.is_deleted.is_(False)))
    days = defaultdict(list)
    for uid, d in db.execute(select(ActivityDay.user_id, ActivityDay.day).where(ActivityDay.group_id == g.id)):
        days[uid].append(d)
    eligible = [v for v in days.values() if (utc_now().date() - min(v)).days >= 13]
    retained = [any(7 <= (d - min(v)).days <= 13 for d in v) for v in eligible]
    acted = recs.get("accepted", 0) + recs.get("dismissed", 0)
    return {
        "median_days_to_settle": dyn.get("median_settle_days") if dyn.get("status") == "ok" else None,
        "unsettled_share": bal["outstanding_total"] / bal["total_spent"] if bal["total_spent"] else None,
        "goal_on_track": float(np.mean([p["projection"]["on_track_pct"] >= 100 or p.get("status") == "achieved"
                                        for p in goals])) if goals else None,
        "recommendation_acceptance": recs.get("accepted", 0) / acted if acted else None,
        "week2_retention": float(np.mean(retained)) if retained else None,
        "wallet_txns_per_week": (paid[0] + imported) / weeks,
        "wallet_taka_per_week": paid[1] / 100 / weeks,
        "expenses_per_week": n_exp / weeks,
    }


def _diff_ci(t: list[float], c: list[float]) -> list[float] | None:
    if len(t) < 2 or len(c) < 2:
        return None
    t, c = np.array(t), np.array(c)
    boots = [RNG.choice(t, len(t)).mean() - RNG.choice(c, len(c)).mean() for _ in range(2000)]
    return [round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3)]


def collect() -> dict:
    name = get_settings().experiment_name
    db = SessionLocal()
    try:
        rows = db.execute(select(ExperimentAssignment, Group).join(Group, Group.id == ExperimentAssignment.group_id)
                          .where(ExperimentAssignment.experiment == name)).all()
        if not rows:
            return {"status": "no_data", "experiment": name,
                    "message": "No randomized groups yet. Set EXPERIMENT_ENABLED=true while the pilot runs."}
        per_arm: dict[str, dict[str, list[float]]] = {"control": defaultdict(list), "treatment": defaultdict(list)}
        n_groups = {"control": 0, "treatment": 0}
        for a, g in rows:
            n_groups[a.arm] += 1
            for k, v in _group_metrics(db, g).items():
                if v is not None:
                    per_arm[a.arm][k].append(float(v))
        results = []
        for key, label, better in OUTCOMES:
            t, c = per_arm["treatment"][key], per_arm["control"][key]
            results.append({"outcome": key, "label": label, "better": better,
                            "treatment_mean": round(float(np.mean(t)), 3) if t else None, "treatment_n": len(t),
                            "control_mean": round(float(np.mean(c)), 3) if c else None, "control_n": len(c),
                            "difference": round(float(np.mean(t) - np.mean(c)), 3) if t and c else None,
                            "difference_ci": _diff_ci(t, c)})
        return {"status": "ok", "experiment": name, "groups": n_groups, "outcomes": results,
                "note": "Group-level randomization; 95% bootstrap intervals over groups. A pilot of a few groups per arm "
                        "gives wide intervals: treat results as direction, not proof."}
    finally:
        db.close()


def to_markdown(m: dict) -> str:
    if m["status"] != "ok":
        return f"# Experiment {m['experiment']}\n\n{m['message']}\n"

    def f(v):
        return "n/a" if v is None else f"{v:,.3g}"

    lines = [f"# Experiment {m['experiment']}: treatment vs control",
             "", f"Groups: treatment {m['groups']['treatment']}, control {m['groups']['control']}.", "",
             "| Outcome | Treatment | Control | Difference (95% CI) | Better if |", "|---|---|---|---|---|"]
    for r in m["outcomes"]:
        ci = f" ({f(r['difference_ci'][0])} to {f(r['difference_ci'][1])})" if r["difference_ci"] else ""
        lines.append(f"| {r['label']} | {f(r['treatment_mean'])} (n={r['treatment_n']}) | {f(r['control_mean'])} "
                     f"(n={r['control_n']}) | {f(r['difference'])}{ci} | {r['better']} |")
    lines += ["", f"_{m['note']}_", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Controlled pilot experiment report")
    ap.add_argument("--out")
    args = ap.parse_args()
    m = collect()
    md = to_markdown(m)
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "experiment.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
        (out / "experiment.md").write_text(md, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
