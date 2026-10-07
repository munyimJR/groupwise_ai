"""Pilot evidence: product metrics from REAL groups (demo sandboxes and synthetic data are excluded).

Run during or after a pilot with student groups who signed up with real accounts:

    python -m scripts.pilot_metrics                # print a summary
    python -m scripts.pilot_metrics --out ../research/results

It reads the configured DATABASE_URL (e.g. Supabase) and reports only aggregate numbers, never names,
descriptions or amounts of individual people. The output feeds the report's "Pilot results" section.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path

from sqlalchemy import func, select

from app.analytics.dynamics import dynamics_report
from app.analytics.goals import plan_goal
from app.config import utc_now
from app.db import SessionLocal
from app.models import (
    AIOutput,
    Expense,
    Goal,
    GoalContribution,
    Group,
    GroupMember,
    PaymentRequest,
    RecommendationAction,
    Settlement,
    User,
    WalletImportItem,
)
from app.services.snapshot import load_snapshot_uncached


def _pct(part: float, whole: float) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def collect(min_expenses: int = 5) -> dict:
    db = SessionLocal()
    try:
        groups = db.scalars(select(Group).join(User, User.id == Group.created_by)
                            .where(User.is_demo.is_(False), User.auth_provider.in_(["local", "supabase"]))).all()
        real_users = db.scalar(select(func.count()).select_from(User).where(
            User.is_demo.is_(False), User.auth_provider.in_(["local", "supabase"])))
        pilot, settle_days, cbis, goal_on_track = [], [], [], []
        for g in groups:
            n_exp = db.scalar(select(func.count()).select_from(Expense).where(Expense.group_id == g.id,
                                                                              Expense.is_deleted.is_(False)))
            if n_exp >= min_expenses:
                pilot.append(g)
        ids = [g.id for g in pilot]
        if not ids:
            return {"status": "no_pilot_data", "real_accounts": real_users,
                    "message": f"No real (non-demo) group has {min_expenses}+ expenses yet."}

        expenses = db.execute(select(Expense.group_id, Expense.category_source, Expense.anomaly_status,
                                     Expense.created_at, Expense.notes)
                              .where(Expense.group_id.in_(ids), Expense.is_deleted.is_(False))).all()
        app_users = db.scalar(select(func.count()).select_from(GroupMember).where(
            GroupMember.group_id.in_(ids), GroupMember.user_id.is_not(None), GroupMember.status == "active"))
        sources = Counter(e.category_source for e in expenses)
        flagged = [e for e in expenses if e.anomaly_status in ("flagged", "valid", "dismissed")]
        reviewed = [e for e in flagged if e.anomaly_status in ("valid", "dismissed")]
        imported = sum(1 for e in expenses if (e.notes or "").startswith("Imported from wallet statement"))

        settlements = db.execute(select(Settlement.note).where(Settlement.group_id.in_(ids))).all()
        via_wallet = sum(1 for s in settlements if (s.note or "").startswith(("Paid via wallet", "Wallet send money")))
        requests = Counter(db.scalars(select(PaymentRequest.status).where(PaymentRequest.group_id.in_(ids))))
        recs = Counter(db.scalars(select(RecommendationAction.action).where(RecommendationAction.group_id.in_(ids))))
        copilot = db.scalar(select(func.count()).select_from(AIOutput).where(AIOutput.group_id.in_(ids),
                                                                             AIOutput.kind == "copilot"))
        wallet_imports = db.scalar(select(func.count()).select_from(WalletImportItem)
                                   .where(WalletImportItem.group_id.in_(ids)))
        contributions = db.scalar(select(func.count()).select_from(GoalContribution).join(Goal)
                                  .where(Goal.group_id.in_(ids)))

        first = min(e.created_at for e in expenses)
        weeks = max((utc_now() - first) / timedelta(days=7), 1.0)
        for g in pilot:
            snap = load_snapshot_uncached(db, g)
            dyn = dynamics_report(snap)
            if dyn.get("status") == "ok":
                cbis.append(dyn["contribution_balance_index"])
                if dyn.get("median_settle_days") is not None:
                    settle_days.append(dyn["median_settle_days"])
            for goal in snap.goals:
                if goal.status == "active":
                    goal_on_track.append(plan_goal(snap, goal)["projection"]["on_track_pct"] >= 100)

        return {
            "status": "ok",
            "pilot": {"groups": len(pilot), "app_users": app_users, "real_accounts": real_users,
                      "weeks_observed": round(weeks, 1), "expenses": len(expenses),
                      "expenses_per_group_per_week": round(len(expenses) / len(pilot) / weeks, 1)},
            "ai_categorization": {"accepted_as_suggested_pct": _pct(sources.get("ai", 0) + sources.get("feedback", 0),
                                                                    len(expenses)),
                                  "corrected_by_user_pct": _pct(sources.get("user", 0), len(expenses))},
            "unusual_expenses": {"flagged": len(flagged), "reviewed_pct": _pct(len(reviewed), len(flagged))},
            "settlement": {"median_days_to_settle": round(statistics.median(settle_days), 1) if settle_days else None,
                           "settlements": len(settlements), "via_wallet_pct": _pct(via_wallet, len(settlements)),
                           "payment_requests": dict(requests)},
            "wallet": {"imported_transactions": wallet_imports, "imported_expenses": imported},
            "recommendations": {"accepted": recs.get("accepted", 0), "dismissed": recs.get("dismissed", 0),
                                "helpful_pct": _pct(recs.get("accepted", 0), sum(recs.values()))},
            "goals": {"active": len(goal_on_track), "on_track_pct": _pct(sum(goal_on_track), len(goal_on_track)),
                      "contributions": contributions},
            "fairness": {"median_contribution_balance_index": round(statistics.median(cbis), 2) if cbis else None},
            "copilot_questions": copilot,
            "note": "Real accounts only (demo sandboxes and synthetic members excluded). Aggregates only.",
        }
    finally:
        db.close()


def _show(value, suffix: str = "") -> str:
    return "n/a" if value is None else f"{value}{suffix}"


def to_markdown(m: dict) -> str:
    if m["status"] != "ok":
        return f"# Pilot metrics\n\n{m['message']} Real accounts so far: {m['real_accounts']}.\n"
    p = m["pilot"]
    rows = [
        ("Pilot groups / app users", f"{p['groups']} / {p['app_users']}"),
        ("Weeks observed", p["weeks_observed"]),
        ("Expenses logged (per group per week)", f"{p['expenses']} ({p['expenses_per_group_per_week']})"),
        ("AI category accepted as suggested", _show(m["ai_categorization"]["accepted_as_suggested_pct"], "%")),
        ("Unusual expenses flagged / reviewed", f"{m['unusual_expenses']['flagged']} / {_show(m['unusual_expenses']['reviewed_pct'], '%')}"),
        ("Median days to settle a debt", _show(m["settlement"]["median_days_to_settle"])),
        ("Settlements done through the wallet", _show(m["settlement"]["via_wallet_pct"], "%")),
        ("Wallet transactions imported", m["wallet"]["imported_transactions"]),
        ("Recommendations marked helpful", _show(m["recommendations"]["helpful_pct"], "%")),
        ("Active goals on track", f"{_show(m['goals']['on_track_pct'], '%')} of {m['goals']['active']}"),
        ("Copilot questions asked", m["copilot_questions"]),
    ]
    table = "\n".join(f"| {k} | {v} |" for k, v in rows)
    return f"# Pilot metrics (real groups)\n\n| Metric | Value |\n|---|---|\n{table}\n\n_{m['note']}_\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", help="folder to write pilot_metrics.json and pilot_metrics.md")
    ap.add_argument("--min-expenses", type=int, default=5)
    args = ap.parse_args()
    m = collect(args.min_expenses)
    md = to_markdown(m)
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "pilot_metrics.json").write_text(json.dumps(m, indent=2), encoding="utf-8")
        (out / "pilot_metrics.md").write_text(md, encoding="utf-8")
        print(f"Wrote {out / 'pilot_metrics.md'}")
    sys.stdout.write(md)


if __name__ == "__main__":
    main()
