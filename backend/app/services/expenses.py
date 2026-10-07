"""Expense lifecycle: categorize → split → score for anomalies → persist → notify."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.splits import compute_split
from ..ml.anomaly import MODEL_NAME as ANOMALY_MODEL
from ..ml.anomaly import MODEL_VERSION as ANOMALY_VERSION
from ..ml.anomaly import GroupAnomalyModel, Txn
from ..ml.categorizer import get_categorizer
from ..ml.taxonomy import SUBCATEGORIES, get_subcategory
from ..ml.text import detect_merchant
from ..models import AIOutput, CategoryFeedback, Expense, ExpenseSplit, Group, GroupMember
from .notifications import notify_members


class ExpenseError(ValueError):
    pass


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def categorize(db: Session, text: str, group_id: str | None = None) -> dict:
    """Model prediction, overridden by this group's own past corrections for the same description."""
    result = get_categorizer().predict(text)
    if group_id:
        fb = db.scalars(
            select(CategoryFeedback).where(CategoryFeedback.group_id == group_id, CategoryFeedback.text == _norm(text)[:240])
            .order_by(CategoryFeedback.created_at.desc())
        ).first()
        if fb and fb.corrected_subcategory in SUBCATEGORIES:
            sub = get_subcategory(fb.corrected_subcategory)
            result = {**result, "subcategory": sub.key, "subcategory_label": sub.label, "category": sub.category,
                      "expense_type": sub.expense_type, "needs_confirmation": False, "source": "feedback",
                      "note": "Learned from a previous correction in this group"}
            return result
    result["source"] = "ai"
    return result


def history_txns(db: Session, group_id: str, exclude_id: str | None = None) -> list[Txn]:
    rows = db.execute(
        select(Expense.id, Expense.amount_paisa, Expense.category, Expense.subcategory, Expense.occurred_at,
               Expense.merchant, Expense.description)
        .where(Expense.group_id == group_id, Expense.is_deleted.is_(False))
    ).all()
    counts: dict[str, int] = {}
    for eid, in db.execute(select(ExpenseSplit.expense_id).join(Expense, Expense.id == ExpenseSplit.expense_id)
                           .where(Expense.group_id == group_id)):
        counts[eid] = counts.get(eid, 0) + 1
    return [Txn(r.id, r.amount_paisa, r.category, r.subcategory, r.occurred_at, counts.get(r.id, 1), r.merchant,
                r.description) for r in rows if r.id != exclude_id]


def score_expense(db: Session, expense: Expense, n_members: int) -> dict:
    history = history_txns(db, expense.group_id, exclude_id=expense.id)
    model = GroupAnomalyModel(history, n_members)
    txn = Txn(expense.id, expense.amount_paisa, expense.category, expense.subcategory, expense.occurred_at,
              len(expense.splits) or 1, expense.merchant, expense.description)
    return model.score(txn)


def apply_anomaly_result(db: Session, expense: Expense, result: dict) -> None:
    expense.anomaly_score = result["score"]
    expense.anomaly_reasons = result["reasons"]
    if result["flagged"]:
        if expense.anomaly_status not in ("valid", "dismissed"):
            expense.anomaly_status = "flagged"
    elif expense.anomaly_status == "flagged":
        expense.anomaly_status = "none"
    db.add(AIOutput(group_id=expense.group_id, kind="anomaly", entity_id=expense.id, model_name=ANOMALY_MODEL,
                    model_version=ANOMALY_VERSION, confidence=result["score"],
                    payload={"flagged": result["flagged"], "signals": result["signals"], "reasons": result["reasons"],
                             "history_count": result["history_count"]}))


def create_expense(db: Session, group: Group, actor_user_id: str | None, *, description: str, amount_paisa: int,
                   payer_member_id: str, participant_ids: list[str], occurred_at: datetime,
                   subcategory: str | None = None, merchant: str | None = None, payment_method: str = "mobile_wallet",
                   split_method: str = "equal", split_values: dict[str, float] | None = None,
                   notes: str | None = None, notify: bool = True) -> tuple[Expense, dict, dict]:
    members = {m.id: m for m in db.scalars(select(GroupMember).where(GroupMember.group_id == group.id))}
    active = {mid for mid, m in members.items() if m.status == "active"}
    if payer_member_id not in active:
        raise ExpenseError("The payer must be an active member of this group.")
    if split_method == "equal":
        bad = [p for p in participant_ids if p not in active]
        if bad or not participant_ids:
            raise ExpenseError("Participants must be active members of this group.")
    shares = compute_split(split_method, amount_paisa, participant_ids, split_values)
    if any(mid not in active for mid in shares):
        raise ExpenseError("Participants must be active members of this group.")

    prediction = categorize(db, description, group.id)
    if subcategory and subcategory in SUBCATEGORIES:
        chosen = get_subcategory(subcategory)
        source = "ai" if subcategory == prediction["subcategory"] else "user"
    else:
        chosen = get_subcategory(prediction["subcategory"])
        source = prediction.get("source", "ai")
    expense = Expense(group_id=group.id, payer_member_id=payer_member_id, created_by_user_id=actor_user_id,
                      amount_paisa=amount_paisa, description=description.strip()[:200],
                      merchant=(merchant or detect_merchant(description) or None),
                      category=chosen.category, subcategory=chosen.key, expense_type=chosen.expense_type,
                      category_source=source, category_confidence=prediction["confidence"], occurred_at=occurred_at,
                      payment_method=payment_method, split_method=split_method, notes=notes)
    expense.splits = [ExpenseSplit(member_id=mid, share_paisa=amt) for mid, amt in shares.items()]
    db.add(expense)
    db.flush()
    if source == "user":
        db.add(CategoryFeedback(group_id=group.id, expense_id=expense.id, user_id=actor_user_id,
                                text=_norm(description)[:240], predicted_subcategory=prediction["subcategory"],
                                corrected_subcategory=chosen.key))
    db.add(AIOutput(group_id=group.id, kind="categorization", entity_id=expense.id, model_name="expense-categorizer",
                    model_version=prediction["model"]["version"], confidence=prediction["confidence"],
                    payload={"predicted": prediction["subcategory"], "chosen": chosen.key, "source": source,
                             "signals": prediction["signals"]}))
    anomaly = score_expense(db, expense, len(active))
    apply_anomaly_result(db, expense, anomaly)
    group.data_version = Group.data_version + 1  # atomic in SQL: no lost updates

    if not notify:  # bulk imports send one summary notification instead
        return expense, prediction, anomaly
    payer_name = members[payer_member_id].display_name
    actor_member = next((m for m in members.values() if m.user_id == actor_user_id), None)
    notify_members(db, group, exclude_user_id=actor_user_id, kind="expense",
                   title=f"New expense in {group.name}",
                   body=f"{actor_member.display_name if actor_member else payer_name} added ৳{amount_paisa / 100:,.0f} · "
                        f"{expense.description}",
                   link=f"/g/{group.id}/transactions/{expense.id}")
    if anomaly["flagged"]:
        notify_members(db, group, exclude_user_id=None, kind="anomaly",
                       title=f"Unusual ৳{amount_paisa / 100:,.0f} expense detected",
                       body=f"“{expense.description}” in {group.name} looks unusual "
                            f"({round(anomaly['score'] * 100)}% anomaly score). Review it before settling up.",
                       link=f"/g/{group.id}/transactions/{expense.id}", dedupe_key=f"anomaly:{expense.id}")
    return expense, prediction, anomaly


def recategorize(db: Session, group: Group, expense: Expense, subcategory: str, user_id: str | None) -> None:
    if subcategory not in SUBCATEGORIES:
        raise ExpenseError("Unknown category.")
    sub = get_subcategory(subcategory)
    previous = expense.subcategory
    expense.category, expense.subcategory, expense.expense_type = sub.category, sub.key, sub.expense_type
    expense.category_source = "user"
    db.add(CategoryFeedback(group_id=group.id, expense_id=expense.id, user_id=user_id, text=_norm(expense.description)[:240],
                            predicted_subcategory=previous, corrected_subcategory=sub.key))
    group.data_version = Group.data_version + 1  # atomic in SQL: no lost updates


