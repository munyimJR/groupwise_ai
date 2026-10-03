"""Check that the demo narrative holds no matter which day the demo is opened.

Demo data is generated relative to "today", so this script regenerates the demo groups for many
different dates and reports the key computed facts (trend, drivers, anomalies, goal status).
Usage:  python -m scripts.check_demo_robustness [days]
"""
from __future__ import annotations

import os
import sys
from datetime import timedelta

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.analytics.goals import plan_goal  # noqa: E402
from app.analytics.spending import spending_report  # noqa: E402
from app.config import local_now  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Group  # noqa: E402
from app.services.snapshot import load_snapshot_uncached  # noqa: E402
from app.synthetic.seed import create_demo_user, seed_workspace  # noqa: E402


def main(days: int = 28) -> None:
    init_db()
    base = local_now()
    for k in range(days):
        today = base - timedelta(days=k)
        db = SessionLocal()
        user = create_demo_user(db, 1)
        seed_workspace(db, user, today)
        db.commit()
        row = []
        for g in db.query(Group).filter(Group.created_by == user.id).all():
            snap = load_snapshot_uncached(db, g)
            snap.as_of = today
            rep = spending_report(snap)
            focus = rep.get("focus") or {}
            drv = rep["drivers"][0]["segment"] if rep["drivers"] else "-"
            flagged = sum(1 for e in snap.expenses if e.anomaly_status == "flagged")
            goal = ""
            for gl in snap.goals:
                goal = f"goal {plan_goal(snap, gl)['projection']['on_track_pct']:.0f}%"
            row.append(f"{g.name[:10]:10} {focus.get('category', '-'):9} {focus.get('change_pct') or 0:+6.1f}% "
                       f"[{drv[:24]:24}] flagged={flagged} {goal}")
        print(today.date(), " | ".join(row[:2]))
        db.close()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 28)
