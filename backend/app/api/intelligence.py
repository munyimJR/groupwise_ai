"""Financial intelligence endpoints: dashboard, insights, analytics, forecast, dynamics, goals, What-If, copilot."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..analytics.dynamics import dynamics_report
from ..analytics.forecasting import group_forecast
from ..analytics.goals import plan_goal
from ..analytics.health import health_score
from ..analytics.insights import build_insights, build_recommendations
from ..analytics.ledger import balances
from ..analytics.spending import spending_report
from ..analytics.whatif import simulate
from ..auth.security import limiter
from ..config import local_now, utc_now
from ..copilot.engine import ask
from ..core.money import MoneyError, to_paisa
from ..db import get_db
from ..llm.client import llm_status
from ..models import AIOutput, Expense, Goal, GoalContribution, GroupMember, RecommendationAction
from ..schemas import ContributionIn, CopilotIn, GoalIn, GoalUpdateIn, RecommendationActionIn, WhatIfIn
from ..services.notifications import notify_members, notify_user
from ..services.snapshot import GroupSnapshot, load_snapshot
from .common import GroupAccess, expense_out, group_access, member_names

router = APIRouter(tags=["intelligence"])


def _snap(db: Session, access: GroupAccess) -> GroupSnapshot:
    return load_snapshot(db, access.group)


def _dismissed(db: Session, access: GroupAccess) -> set[str]:
    since = utc_now() - timedelta(days=7)
    return set(db.scalars(select(RecommendationAction.recommendation_key).where(
        RecommendationAction.group_id == access.group.id, RecommendationAction.user_id == access.user.id,
        RecommendationAction.action == "dismissed", RecommendationAction.created_at >= since)))


def _sync_insight_notifications(db: Session, access: GroupAccess, insights: list[dict]) -> None:
    """Turn important insights into (deduplicated) notifications for the signed-in user."""
    week = local_now().isocalendar()
    for ins in insights:
        if ins["kind"] == "goal" and ins["severity"] == "warning":
            key = f"goal:{ins['evidence']['goal_id']}:{week.year}-{week.week}"
        elif ins["kind"] == "forecast" and ins["evidence"].get("pressure_days"):
            key = f"forecast:{access.group.id}:{week.year}-{week.week}"
        elif ins["kind"] == "spending_trend":
            key = f"trend:{access.group.id}:{ins['evidence']['category']}:{week.year}-{week.week}"
        else:
            continue
        notify_user(db, access.user.id, access.group.id, "insight", ins["title"],
                    (ins.get("inference") or ins["observation"])[:400], (ins.get("action") or {}).get("link"),
                    dedupe_key=key)
    db.commit()


@router.get("/groups/{group_id}/dashboard")
def dashboard(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    snap = _snap(db, access)
    me = access.member.id
    bal = balances(snap)
    mine = next((m for m in bal["members"] if m["member_id"] == me), None)
    spend = spending_report(snap, 30)
    insights = build_insights(snap, me)
    recs = build_recommendations(snap, _dismissed(db, access), me)
    fc = group_forecast(snap, 7)
    goals = [plan_goal(snap, g) for g in snap.goals if g.status == "active"]
    dyn = dynamics_report(snap, me)
    _sync_insight_notifications(db, access, insights)
    recent = db.scalars(select(Expense).options(selectinload(Expense.splits))
                        .where(Expense.group_id == access.group.id, Expense.is_deleted.is_(False))
                        .order_by(Expense.occurred_at.desc()).limit(6)).all()
    names = member_names(db, access.group.id)
    return {
        "group": {"id": access.group.id, "name": access.group.name, "group_type": access.group.group_type,
                  "member_count": len(snap.active_members), "monthly_budget": access.group.monthly_budget_paisa},
        "me": {"member_id": me, "name": access.member.display_name, "net": mine["net"] if mine else 0,
               "paid": mine["paid"] if mine else 0, "share": mine["share"] if mine else 0},
        "spending": {k: spend[k] for k in ("total", "previous_total", "change_pct", "change_pct_excluding_unusual", "count",
                                           "average_expense", "categories", "daily_series", "period_days", "basis")},
        "health": health_score(snap),
        "insights": insights,
        "recommendation": recs[0] if recs else None,
        "recommendations": recs,
        "forecast": fc,
        "goals": goals,
        "dynamics": {"status": dyn.get("status"), "insights": dyn.get("insights", []),
                     "contribution_balance_index": dyn.get("contribution_balance_index"),
                     "members": dyn.get("members", [])[:5]},
        "balances": {"outstanding_total": bal["outstanding_total"], "simplified_transfer_count": bal["simplified_transfer_count"],
                     "naive_transfer_count": bal["naive_transfer_count"]},
        "recent_expenses": [expense_out(e, names) for e in recent],
        "llm": llm_status(),
        "as_of": snap.as_of.isoformat(),
    }


@router.get("/groups/{group_id}/insights")
def insights(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    snap = _snap(db, access)
    return {"insights": build_insights(snap, access.member.id),
            "recommendations": build_recommendations(snap, _dismissed(db, access), access.member.id),
            "anomalies": _anomaly_list(db, access)}


@router.get("/groups/{group_id}/analytics/spending")
def spending(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db),
             days: int = Query(30, ge=7, le=180)) -> dict:
    return spending_report(_snap(db, access), days)


@router.get("/groups/{group_id}/balances")
def get_balances(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    bal = balances(_snap(db, access))
    return {**bal, "members": [{**m, "is_you": m["member_id"] == access.member.id} for m in bal["members"]],
            "transfers": [{**t, "involves_you": access.member.id in (t["from_member_id"], t["to_member_id"])}
                          for t in bal["transfers"]],
            "my_member_id": access.member.id}


@router.get("/groups/{group_id}/forecast")
def forecast(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db),
             horizon: int = Query(7, ge=7, le=30)) -> dict:
    result = group_forecast(_snap(db, access), horizon)
    if result.get("status") == "ok":
        db.add(AIOutput(group_id=access.group.id, kind="forecast", model_name=result["model"]["name"],
                        model_version=result["model"]["version"],
                        confidence={"high": 0.8, "medium": 0.6, "low": 0.4}[result["confidence"]],
                        payload={"horizon": horizon, "total": result["total"], "interval": result["interval"]}))
        db.commit()
    return result


@router.get("/groups/{group_id}/dynamics")
def dynamics(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    return dynamics_report(_snap(db, access), access.member.id)


@router.get("/groups/{group_id}/health")
def health(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    return health_score(_snap(db, access))


def _anomaly_list(db: Session, access: GroupAccess) -> list[dict]:
    rows = db.scalars(select(Expense).where(Expense.group_id == access.group.id, Expense.is_deleted.is_(False),
                                            Expense.anomaly_status.in_(["flagged", "valid", "dismissed"]))
                      .order_by(Expense.occurred_at.desc()).limit(20)).all()
    names = member_names(db, access.group.id)
    return [expense_out(e, names, detail=False) | {"reasons": e.anomaly_reasons or []} for e in rows]


@router.get("/groups/{group_id}/anomalies")
def anomalies(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> list[dict]:
    return _anomaly_list(db, access)


# ----------------------------------------------------------------------------- goals
def _goal(db: Session, access: GroupAccess, goal_id: str) -> Goal:
    g = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.group_id == access.group.id))
    if g is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Goal not found.")
    return g


@router.get("/groups/{group_id}/goals")
def list_goals(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> list[dict]:
    snap = _snap(db, access)
    return [plan_goal(snap, g) | {"status_label": g.status} for g in snap.goals if g.status != "archived"]


@router.post("/groups/{group_id}/goals", status_code=201)
def create_goal(body: GoalIn, access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    today = local_now().date()
    start = body.start_date or today
    if body.deadline <= today:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="The deadline must be in the future.")
    try:
        target = to_paisa(body.target)
    except MoneyError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    g = Goal(group_id=access.group.id, title=body.title.strip(), description=body.description, target_paisa=target,
             start_date=start, deadline=body.deadline, created_by_user_id=access.user.id)
    db.add(g)
    access.group.data_version += 1
    notify_members(db, access.group, exclude_user_id=access.user.id, kind="goal", title=f"New goal in {access.group.name}",
                   body=f"{access.member.display_name} created “{g.title}” — target ৳{target / 100:,.0f}.",
                   link=f"/g/{access.group.id}/goals")
    db.commit()
    snap = _snap(db, access)
    goal = next(x for x in snap.goals if x.id == g.id)
    return plan_goal(snap, goal)


@router.get("/groups/{group_id}/goals/{goal_id}")
def get_goal(goal_id: str, access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    _goal(db, access, goal_id)
    snap = _snap(db, access)
    goal = next(x for x in snap.goals if x.id == goal_id)
    plan = plan_goal(snap, goal)
    names = member_names(db, access.group.id)
    contributions = db.scalars(select(GoalContribution).where(GoalContribution.goal_id == goal_id)
                               .order_by(GoalContribution.occurred_at.desc()).limit(20)).all()
    return {**plan, "recent_contributions": [{"id": c.id, "member_id": c.member_id, "name": names.get(c.member_id),
                                              "amount": c.amount_paisa, "occurred_at": c.occurred_at.isoformat(),
                                              "note": c.note} for c in contributions]}


@router.patch("/groups/{group_id}/goals/{goal_id}")
def update_goal(goal_id: str, body: GoalUpdateIn, access: GroupAccess = Depends(group_access),
                db: Session = Depends(get_db)) -> dict:
    g = _goal(db, access, goal_id)
    if body.title is not None:
        g.title = body.title.strip()
    if body.description is not None:
        g.description = body.description
    if body.target is not None:
        g.target_paisa = to_paisa(body.target)
    if body.deadline is not None:
        g.deadline = body.deadline
    if body.status is not None:
        g.status = body.status
    access.group.data_version += 1
    db.commit()
    return get_goal(goal_id, access, db)


@router.delete("/groups/{group_id}/goals/{goal_id}")
def delete_goal(goal_id: str, access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    g = _goal(db, access, goal_id)
    g.status = "archived"
    access.group.data_version += 1
    db.commit()
    return {"ok": True}


@router.post("/groups/{group_id}/goals/{goal_id}/contributions", status_code=201)
def add_contribution(goal_id: str, body: ContributionIn, access: GroupAccess = Depends(group_access),
                     db: Session = Depends(get_db)) -> dict:
    _goal(db, access, goal_id)
    if not db.scalar(select(GroupMember.id).where(GroupMember.id == body.member_id, GroupMember.group_id == access.group.id)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Choose a member of this group.")
    try:
        amount = to_paisa(body.amount)
    except MoneyError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    when = body.occurred_at.replace(tzinfo=None) if body.occurred_at else local_now()
    db.add(GoalContribution(goal_id=goal_id, member_id=body.member_id, amount_paisa=amount, occurred_at=when,
                            note=body.note))
    access.group.data_version += 1
    db.commit()
    return get_goal(goal_id, access, db)


# ----------------------------------------------------------------------------- what-if, copilot, recommendations
@router.post("/groups/{group_id}/what-if")
def what_if(body: WhatIfIn, access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    return simulate(_snap(db, access), body.category_changes, body.overall_change_pct,
                    body.extra_monthly_contribution * 100, body.goal_id, body.redirect_savings, access.member.id)


@router.post("/groups/{group_id}/copilot")
def copilot(body: CopilotIn, request: Request, access: GroupAccess = Depends(group_access),
            db: Session = Depends(get_db)) -> dict:
    limiter.check(request, "copilot", 30, 60)
    result = ask(_snap(db, access), body.question, access.member.id, [t.model_dump() for t in body.history])
    db.add(AIOutput(group_id=access.group.id, kind="copilot", model_name="ask-groupwise",
                    model_version=result["llm"]["model"] or "template-1.0", confidence=result["intent"]["confidence"],
                    payload={"question": result["question"][:300], "intent": result["intent"]["name"], "mode": result["mode"],
                             "grounding": result["grounding"], "cited": result["cited_fact_ids"]}))
    db.commit()
    return result


@router.post("/groups/{group_id}/recommendations/{key}/action")
def recommendation_action(key: str, body: RecommendationActionIn, access: GroupAccess = Depends(group_access),
                          db: Session = Depends(get_db)) -> dict:
    db.add(RecommendationAction(group_id=access.group.id, user_id=access.user.id, recommendation_key=key[:80],
                                action=body.action))
    db.commit()
    return {"ok": True, "message": "Noted — thanks. You stay in control: GroupWise only suggests."
            if body.action == "accepted" else "Hidden for 7 days."}


@router.get("/groups/{group_id}/ai-log")
def ai_log(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db),
           limit: int = Query(20, ge=1, le=100)) -> list[dict]:
    rows = db.scalars(select(AIOutput).where(AIOutput.group_id == access.group.id)
                      .order_by(AIOutput.created_at.desc()).limit(limit)).all()
    return [{"id": r.id, "kind": r.kind, "model_name": r.model_name, "model_version": r.model_version,
             "confidence": r.confidence, "entity_id": r.entity_id, "payload": r.payload,
             "created_at": r.created_at.isoformat() + "Z"} for r in rows]
