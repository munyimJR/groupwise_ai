"""Seed a user's workspace with the demo scenarios.

Synthetic transactions go through the *same* models the live product uses:
  * the categorizer labels each description (where it disagrees with the scenario's ground truth,
    the expense is stored as a human correction — category_source="user"),
  * the anomaly detector scores every expense against the group's history.
Older alerts (> 30 days) are stored as already reviewed, as an active group would have done.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import insert
from sqlalchemy.orm import Session

from ..config import local_now, utc_now
from ..ml.anomaly import Txn, score_all
from ..ml.categorizer import get_categorizer
from ..ml.taxonomy import get_subcategory
from ..models import (
    Expense,
    ExpenseSplit,
    Goal,
    GoalContribution,
    Group,
    GroupMember,
    Settlement,
    User,
    new_id,
)
from ..services.notifications import notify_user
from .generator import GeneratedGroup, generate_group
from .scenarios import PRIMARY, demo_scenarios


def _seed_group(db: Session, user: User, gen: GeneratedGroup, today: datetime) -> Group:
    sc = gen.scenario
    first = min((e.occurred_at for e in gen.expenses), default=today)
    group = Group(id=new_id(), name=sc.name, description=sc.description, group_type=sc.group_type,
                  created_by=user.id, created_at=first - timedelta(hours=6), data_version=1,
                  monthly_budget_paisa=int(sc.monthly_budget * 100) if sc.monthly_budget else None)
    db.add(group)
    member_ids: dict[str, str] = {}
    for spec in sc.members:
        mid = new_id()
        member_ids[spec.key] = mid
        primary = spec.key == PRIMARY
        db.add(GroupMember(id=mid, group_id=group.id, user_id=user.id if primary else None,
                           display_name=user.display_name if primary else spec.name,
                           role="owner" if primary else "member", avatar_color=spec.color,
                           joined_at=first - timedelta(hours=6)))
    db.flush()

    model = get_categorizer()
    probs = model.predict_proba([e.description for e in gen.expenses]) if gen.expenses else []
    expense_rows, split_rows, txns = [], [], []
    for e, p in zip(gen.expenses, probs):
        eid = new_id()
        best = model.classes_[int(p.argmax())]
        truth = get_subcategory(e.subcategory)
        expense_rows.append({
            "id": eid, "group_id": group.id, "payer_member_id": member_ids[e.payer],
            "created_by_user_id": user.id if e.payer == PRIMARY else None, "amount_paisa": e.amount_paisa,
            "description": e.description, "merchant": e.merchant, "category": truth.category,
            "subcategory": truth.key, "expense_type": truth.expense_type,
            "category_source": "ai" if best == truth.key else "user", "category_confidence": round(float(p.max()), 3),
            "occurred_at": e.occurred_at, "payment_method": e.payment_method, "split_method": "equal",
            "created_at": e.occurred_at - timedelta(hours=6), "anomaly_status": "none", "is_deleted": False,
        })
        for mk, share in e.shares.items():
            split_rows.append({"id": new_id(), "expense_id": eid, "member_id": member_ids[mk], "share_paisa": share})
        txns.append(Txn(eid, e.amount_paisa, truth.category, truth.key, e.occurred_at, len(e.shares), e.merchant,
                        e.description))

    scores = score_all(txns, len(sc.members))
    recent_cutoff = today - timedelta(days=30)
    for row, gen_e in zip(expense_rows, gen.expenses):
        res = scores[row["id"]]
        row["anomaly_score"] = res["score"]
        row["anomaly_reasons"] = res["reasons"]
        if res["flagged"]:
            if gen_e.reviewed_valid or row["occurred_at"] < recent_cutoff:
                row["anomaly_status"] = "valid"
            else:
                row["anomaly_status"] = "flagged"
    if expense_rows:
        db.execute(insert(Expense), expense_rows)
        db.execute(insert(ExpenseSplit), split_rows)
    if gen.settlements:
        db.execute(insert(Settlement), [
            {"id": new_id(), "group_id": group.id, "from_member_id": member_ids[s.from_member],
             "to_member_id": member_ids[s.to_member], "amount_paisa": s.amount_paisa, "occurred_at": s.occurred_at,
             "note": "Settled via mobile wallet", "created_at": s.occurred_at - timedelta(hours=6)}
            for s in gen.settlements])
    for g in gen.goals:
        goal = Goal(id=new_id(), group_id=group.id, title=g.spec.title, description=g.spec.description,
                    target_paisa=int(g.spec.target * 100), start_date=g.start, deadline=g.deadline,
                    created_by_user_id=user.id,
                    created_at=datetime.combine(g.start, datetime.min.time()) - timedelta(hours=6))
        db.add(goal)
        db.flush()
        if g.contributions:
            db.execute(insert(GoalContribution), [
                {"id": new_id(), "goal_id": goal.id, "member_id": member_ids[c.member], "amount_paisa": c.amount_paisa,
                 "occurred_at": c.occurred_at, "note": None, "created_at": c.occurred_at - timedelta(hours=6)}
                for c in g.contributions])

    # Activity notifications derived from the seeded data
    for row in expense_rows:
        if row["anomaly_status"] == "flagged":
            notify_user(db, user.id, group.id, "anomaly", f"Unusual ৳{row['amount_paisa'] / 100:,.0f} expense detected",
                        f"“{row['description']}” in {group.name} looks unusual "
                        f"({round(row['anomaly_score'] * 100)}% anomaly score). Review it before settling up.",
                        f"/g/{group.id}/transactions/{row['id']}", dedupe_key=f"anomaly:{row['id']}")
    others = [r for r in expense_rows if r["payer_member_id"] != member_ids[PRIMARY]][-2:]
    names = {v: k for k, v in member_ids.items()}
    spec_names = {m.key: m.name for m in sc.members}
    for r in others:
        who = spec_names[names[r["payer_member_id"]]].split()[0]
        notify_user(db, user.id, group.id, "expense", f"New expense in {group.name}",
                    f"{who} added ৳{r['amount_paisa'] / 100:,.0f} · {r['description']}",
                    f"/g/{group.id}/transactions/{r['id']}", dedupe_key=f"expense:{r['id']}")
    return group


def seed_workspace(db: Session, user: User, today: datetime | None = None) -> list[Group]:
    today = today or local_now()
    groups = [_seed_group(db, user, generate_group(sc, today), today) for sc in demo_scenarios()]
    db.flush()
    return groups


def create_demo_user(db: Session, ttl_hours: int) -> User:
    user = User(id=new_id(), display_name="Ayaan Rahman", auth_provider="demo", is_demo=True,
                avatar_color="#0057B8", expires_at=utc_now() + timedelta(hours=ttl_hours))
    db.add(user)
    db.flush()
    return user
