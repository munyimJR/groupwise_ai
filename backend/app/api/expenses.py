"""Expenses, categorization, anomaly review and settlements."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..auth.security import get_current_user
from ..config import local_now
from ..core.money import MoneyError, to_paisa
from ..core.splits import SplitError, compute_split
from ..db import get_db
from ..ml.taxonomy import SUBCATEGORIES, get_subcategory
from ..ml.text import parse_expense_text
from ..models import Expense, ExpenseSplit, GroupMember, Settlement, User
from ..schemas import CategorizeIn, CategoryIn, ExpenseCreateIn, ExpenseUpdateIn, ReviewIn, SettlementIn
from ..services.expenses import ExpenseError, apply_anomaly_result, categorize, create_expense, recategorize, score_expense
from ..services.notifications import notify_members
from .common import GroupAccess, expense_out, group_access, member_names

router = APIRouter(tags=["expenses"])


def _naive_local(dt):
    if dt is None:
        return local_now()
    if dt.tzinfo is not None:  # convert to Asia/Dhaka wall-clock
        from ..config import LOCAL_TZ

        dt = dt.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return dt.replace(microsecond=0)


@router.post("/categorize")
def categorize_text(body: CategorizeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    parsed = parse_expense_text(body.text)
    group_id = None
    if body.group_id and db.scalar(select(GroupMember.id).where(GroupMember.group_id == body.group_id,
                                                                GroupMember.user_id == user.id)):
        group_id = body.group_id
    result = categorize(db, parsed.description, group_id)
    return {"parsed": {"description": parsed.description, "amount": parsed.amount, "merchant": parsed.merchant},
            "prediction": result}


@router.get("/groups/{group_id}/expenses")
def list_expenses(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db),
                  limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0),
                  category: str | None = None, q: str | None = Query(None, max_length=80),
                  flagged: bool = False, member_id: str | None = None) -> dict:
    stmt = select(Expense).where(Expense.group_id == access.group.id, Expense.is_deleted.is_(False))
    if category:
        stmt = stmt.where(Expense.category == category)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(Expense.description).like(like), func.lower(Expense.merchant).like(like)))
    if flagged:
        stmt = stmt.where(Expense.anomaly_status.in_(["flagged", "valid", "dismissed"]), Expense.anomaly_score >= 0.6)
    if member_id:
        stmt = stmt.where(Expense.payer_member_id == member_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.options(selectinload(Expense.splits)).order_by(Expense.occurred_at.desc())
                      .limit(limit).offset(offset)).all()
    names = member_names(db, access.group.id)
    return {"items": [expense_out(e, names) for e in rows], "total": total, "limit": limit, "offset": offset}


@router.post("/groups/{group_id}/expenses", status_code=201)
def add_expense(body: ExpenseCreateIn, access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    try:
        amount = to_paisa(body.amount)
        split_values = body.split_values
        if body.split_method == "exact" and split_values:
            split_values = {k: to_paisa(v) for k, v in split_values.items() if v > 0}
        participants = body.participant_ids or ([*split_values.keys()] if split_values else [])
        expense, prediction, anomaly = create_expense(
            db, access.group, access.user.id, description=body.description, amount_paisa=amount,
            payer_member_id=body.payer_member_id, participant_ids=participants,
            occurred_at=_naive_local(body.occurred_at), subcategory=body.subcategory, merchant=body.merchant,
            payment_method=body.payment_method, split_method=body.split_method, split_values=split_values,
            notes=body.notes)
    except (MoneyError, SplitError, ExpenseError) as exc:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    db.commit()
    names = member_names(db, access.group.id)
    return {"expense": expense_out(expense, names, detail=True), "categorization": prediction, "anomaly": anomaly}


def _get_expense(db: Session, access: GroupAccess, expense_id: str) -> Expense:
    e = db.scalar(select(Expense).options(selectinload(Expense.splits))
                  .where(Expense.id == expense_id, Expense.group_id == access.group.id, Expense.is_deleted.is_(False)))
    if e is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Expense not found.")
    return e


@router.get("/groups/{group_id}/expenses/{expense_id}")
def get_expense(expense_id: str, access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    e = _get_expense(db, access, expense_id)
    out = expense_out(e, member_names(db, access.group.id), detail=True)
    out["can_edit"] = True
    return out


@router.patch("/groups/{group_id}/expenses/{expense_id}")
def update_expense(expense_id: str, body: ExpenseUpdateIn, access: GroupAccess = Depends(group_access),
                   db: Session = Depends(get_db)) -> dict:
    e = _get_expense(db, access, expense_id)
    active = set(db.scalars(select(GroupMember.id).where(GroupMember.group_id == access.group.id,
                                                         GroupMember.status == "active")))
    try:
        if body.description is not None:
            e.description = body.description.strip()
        if body.occurred_at is not None:
            e.occurred_at = _naive_local(body.occurred_at)
        if body.payer_member_id is not None:
            if body.payer_member_id not in active:
                raise ExpenseError("The payer must be an active member of this group.")
            e.payer_member_id = body.payer_member_id
        if body.notes is not None:
            e.notes = body.notes
        if body.amount is not None or body.participant_ids is not None:
            amount = to_paisa(body.amount) if body.amount is not None else e.amount_paisa
            parts = body.participant_ids if body.participant_ids is not None else [s.member_id for s in e.splits]
            if any(p not in active for p in parts):
                raise ExpenseError("Participants must be active members of this group.")
            shares = compute_split("equal", amount, parts)
            e.amount_paisa = amount
            e.split_method = "equal"
            e.splits.clear()
            db.flush()
            e.splits.extend(ExpenseSplit(member_id=mid, share_paisa=v) for mid, v in shares.items())
        if body.subcategory is not None and body.subcategory != e.subcategory:
            recategorize(db, access.group, e, body.subcategory, access.user.id)
    except (MoneyError, SplitError, ExpenseError) as exc:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    db.flush()
    if e.anomaly_status in ("flagged", "none"):
        n_active = len(active)
        apply_anomaly_result(db, e, score_expense(db, e, n_active))
    access.group.data_version += 1
    db.commit()
    return expense_out(e, member_names(db, access.group.id), detail=True)


@router.delete("/groups/{group_id}/expenses/{expense_id}")
def delete_expense(expense_id: str, access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    e = _get_expense(db, access, expense_id)
    e.is_deleted = True
    access.group.data_version += 1
    db.commit()
    return {"ok": True}


@router.post("/groups/{group_id}/expenses/{expense_id}/review")
def review_anomaly(expense_id: str, body: ReviewIn, access: GroupAccess = Depends(group_access),
                   db: Session = Depends(get_db)) -> dict:
    """Human oversight: AI flags, people decide. Nothing is ever blocked automatically."""
    e = _get_expense(db, access, expense_id)
    e.anomaly_status = {"valid": "valid", "dismiss": "dismissed", "reopen": "flagged"}[body.action]
    access.group.data_version += 1
    db.commit()
    return expense_out(e, member_names(db, access.group.id), detail=True)


@router.post("/groups/{group_id}/expenses/{expense_id}/category")
def correct_category(expense_id: str, body: CategoryIn, access: GroupAccess = Depends(group_access),
                     db: Session = Depends(get_db)) -> dict:
    if body.subcategory not in SUBCATEGORIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown category.")
    e = _get_expense(db, access, expense_id)
    recategorize(db, access.group, e, body.subcategory, access.user.id)
    db.commit()
    sub = get_subcategory(body.subcategory)
    return {"expense": expense_out(e, member_names(db, access.group.id), detail=True),
            "message": f"Saved as {sub.category} › {sub.label}. GroupWise will remember this for similar expenses."}


# ----------------------------------------------------------------------------- settlements
@router.get("/groups/{group_id}/settlements")
def list_settlements(access: GroupAccess = Depends(group_access), db: Session = Depends(get_db),
                     limit: int = Query(30, ge=1, le=100)) -> list[dict]:
    names = member_names(db, access.group.id)
    rows = db.scalars(select(Settlement).where(Settlement.group_id == access.group.id)
                      .order_by(Settlement.occurred_at.desc()).limit(limit)).all()
    return [{"id": s.id, "from_member_id": s.from_member_id, "from_name": names.get(s.from_member_id),
             "to_member_id": s.to_member_id, "to_name": names.get(s.to_member_id), "amount": s.amount_paisa,
             "occurred_at": s.occurred_at.isoformat(), "note": s.note} for s in rows]


@router.post("/groups/{group_id}/settlements", status_code=201)
def record_settlement(body: SettlementIn, access: GroupAccess = Depends(group_access), db: Session = Depends(get_db)) -> dict:
    members = {m.id: m for m in db.scalars(select(GroupMember).where(GroupMember.group_id == access.group.id))}
    if body.from_member_id not in members or body.to_member_id not in members or body.from_member_id == body.to_member_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Choose two different members of this group.")
    try:
        amount = to_paisa(body.amount)
    except MoneyError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    s = Settlement(group_id=access.group.id, from_member_id=body.from_member_id, to_member_id=body.to_member_id,
                   amount_paisa=amount, occurred_at=_naive_local(body.occurred_at), note=body.note,
                   created_by_user_id=access.user.id)
    db.add(s)
    access.group.data_version += 1
    notify_members(db, access.group, exclude_user_id=access.user.id, kind="settlement",
                   title=f"Settlement recorded in {access.group.name}",
                   body=f"{members[body.from_member_id].display_name} paid {members[body.to_member_id].display_name} "
                        f"৳{amount / 100:,.0f}.", link=f"/g/{access.group.id}/balances")
    db.commit()
    return {"id": s.id, "amount": s.amount_paisa}
