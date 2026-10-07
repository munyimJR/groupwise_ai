"""Mobile-wallet flows: import a wallet statement into a group, and pay or save through the wallet.

Statement import turns real wallet transactions into shared expenses and settlements (the AI
categorizes each one and suggests what to do; the person confirms). Payment requests move money
through the wallet and are recorded only when the wallet reports success with a signed event.
"""
from __future__ import annotations

import random
import re
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import get_settings, local_now, utc_now
from ..core.money import MAX_AMOUNT_PAISA
from ..integrations.wallet import SandboxWallet, StatementRow, new_reference, parse_statement
from ..ml.taxonomy import get_subcategory
from ..models import Goal, GoalContribution, Group, GroupMember, PaymentRequest, Settlement, WalletImportItem
from .expenses import categorize, create_expense
from .notifications import notify_members

# Subcategories that are usually shared in student groups; the rest default to "personal, skip".
SHARED_SUBCATEGORIES = {
    "restaurant", "fast_food", "food_delivery", "cafe_snacks", "supermarket", "fresh_market", "ride_hailing",
    "rickshaw_cng", "bus_train", "fuel", "accommodation", "tours_activities", "flights", "rent",
    "household_supplies", "home_services", "electricity", "gas", "water", "internet", "movies", "gaming", "events",
}
KIND_LABELS = {
    "payment": "Payment", "bill_pay": "Bill payment", "recharge": "Mobile recharge", "send_money": "Send money",
    "received": "Received money", "cash_out": "Cash out", "cash_in": "Cash in", "add_money": "Add money",
    "other": "Other",
}
MAX_IMPORT = 200


class WalletError(ValueError):
    pass


def _first_names(member: GroupMember) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", member.display_name.lower()) if len(w) >= 3}


def _match_member(counterparty: str, members: list[GroupMember]) -> GroupMember | None:
    words = set(re.findall(r"[a-z]+", counterparty.lower()))
    hits = [m for m in members if _first_names(m) & words]
    return hits[0] if len(hits) == 1 else None


def _already_imported(db: Session, group_id: str, member_id: str) -> set[str]:
    return set(db.scalars(select(WalletImportItem.provider_txn_id).where(WalletImportItem.group_id == group_id,
                                                                         WalletImportItem.member_id == member_id)))


def _suggest(db: Session, group: Group, me: GroupMember, others: list[GroupMember], row: StatementRow) -> dict:
    out = {
        "txn_id": row.txn_id, "line": row.line, "occurred_at": row.occurred_at.isoformat(), "kind": row.kind,
        "kind_label": KIND_LABELS.get(row.kind, "Other"), "direction": row.direction, "counterparty": row.counterparty,
        "description": row.description, "amount": row.amount_paisa, "suggestion": "skip", "reason": "",
        "category": None, "subcategory": None, "subcategory_label": None, "confidence": None,
        "to_member_id": None, "to_member_name": None,
    }
    if row.amount_paisa <= 0 or row.amount_paisa > MAX_AMOUNT_PAISA:
        out["reason"] = "Amount out of range"
        return out
    if row.direction == "in":
        out["reason"] = "Money you received is not a group expense"
        return out
    if row.kind in ("cash_out", "cash_in", "add_money", "other"):
        out["reason"] = "Wallet top-up or cash withdrawal, not a purchase"
        return out
    if row.kind == "send_money":
        member = _match_member(row.counterparty, others)
        if member:
            out.update(suggestion="settlement", to_member_id=member.id, to_member_name=member.display_name,
                       reason=f"Looks like you paid {member.display_name} back")
        else:
            out["reason"] = "Money sent to someone outside this group"
        return out
    text = " ".join(x for x in (row.description, row.counterparty) if x).strip() or KIND_LABELS[row.kind]
    if row.kind == "recharge":
        pred = {"subcategory": "mobile_recharge", "confidence": 1.0}
    else:
        pred = categorize(db, text, group.id)
    sub = get_subcategory(pred["subcategory"])
    out.update(category=sub.category, subcategory=sub.key, subcategory_label=sub.label,
               confidence=round(float(pred["confidence"]), 3))
    if sub.key in SHARED_SUBCATEGORIES:
        out.update(suggestion="expense", reason=f"{sub.label} is usually shared")
    else:
        out["reason"] = f"{sub.label} is usually personal"
    return out


def preview_statement(db: Session, group: Group, me: GroupMember, text: str) -> dict:
    rows = parse_statement(text)
    others = list(db.scalars(select(GroupMember).where(GroupMember.group_id == group.id, GroupMember.status == "active",
                                                       GroupMember.id != me.id)))
    done = _already_imported(db, group.id, me.id)
    items = []
    for row in sorted(rows, key=lambda r: r.occurred_at, reverse=True):
        item = _suggest(db, group, me, others, row)
        item["already_imported"] = row.txn_id in done
        if item["already_imported"]:
            item["suggestion"], item["reason"] = "skip", "Already imported into this group"
        items.append(item)
    outflow = sum(i["amount"] for i in items if i["direction"] == "out")
    return {
        "items": items,
        "summary": {"rows": len(items), "expenses": sum(i["suggestion"] == "expense" for i in items),
                    "settlements": sum(i["suggestion"] == "settlement" for i in items),
                    "skipped": sum(i["suggestion"] == "skip" for i in items),
                    "already_imported": sum(i["already_imported"] for i in items), "total_out": outflow},
        "method": "Wallet statement parsed by column meaning; each purchase categorized by the expense model; "
                  "shared vs personal and paid-back suggestions are rules you can change.",
    }


def import_statement(db: Session, group: Group, me: GroupMember, actor_user_id: str, text: str,
                     selections: list[dict], participant_ids: list[str]) -> dict:
    if len(selections) > MAX_IMPORT:
        raise WalletError(f"Import up to {MAX_IMPORT} transactions at a time.")
    rows = {r.txn_id: r for r in parse_statement(text)}
    members = {m.id: m for m in db.scalars(select(GroupMember).where(GroupMember.group_id == group.id,
                                                                     GroupMember.status == "active"))}
    done = _already_imported(db, group.id, me.id)
    created_expenses, created_settlements, skipped, flagged = 0, 0, 0, 0
    for sel in selections:
        row = rows.get(sel.get("txn_id", ""))
        if row is None or row.txn_id in done or row.direction != "out" or row.amount_paisa > MAX_AMOUNT_PAISA:
            skipped += 1
            continue
        action = sel.get("action")
        if action == "expense":
            if row.kind not in ("payment", "bill_pay", "recharge"):
                skipped += 1
                continue
            description = (sel.get("description") or row.description or row.counterparty or "Wallet payment").strip()
            expense, _, anomaly = create_expense(
                db, group, actor_user_id, description=description[:200], amount_paisa=row.amount_paisa,
                payer_member_id=me.id, participant_ids=participant_ids, occurred_at=row.occurred_at,
                subcategory=sel.get("subcategory"), merchant=row.counterparty or None, payment_method="mobile_wallet",
                notes=f"Imported from wallet statement · TrxID {row.txn_id}", notify=False)
            entity_id = expense.id
            created_expenses += 1
            flagged += bool(anomaly["flagged"])
        elif action == "settlement":
            to_id = sel.get("to_member_id")
            if row.kind != "send_money" or to_id not in members or to_id == me.id:
                skipped += 1
                continue
            s = Settlement(group_id=group.id, from_member_id=me.id, to_member_id=to_id, amount_paisa=row.amount_paisa,
                           occurred_at=row.occurred_at, note=f"Wallet send money · TrxID {row.txn_id}",
                           created_by_user_id=actor_user_id)
            db.add(s)
            db.flush()
            entity_id = s.id
            created_settlements += 1
        else:
            skipped += 1
            continue
        db.add(WalletImportItem(group_id=group.id, member_id=me.id, provider_txn_id=row.txn_id, kind=action,
                                entity_id=entity_id))
        done.add(row.txn_id)
    if created_expenses or created_settlements:
        group.data_version = Group.data_version + 1  # atomic in SQL: no lost updates
        parts = []
        if created_expenses:
            parts.append(f"{created_expenses} expense{'s' if created_expenses != 1 else ''}")
        if created_settlements:
            parts.append(f"{created_settlements} payment{'s' if created_settlements != 1 else ''} back")
        notify_members(db, group, exclude_user_id=actor_user_id, kind="expense",
                       title=f"Wallet import in {group.name}",
                       body=f"{me.display_name} imported {' and '.join(parts)} from a wallet statement.",
                       link=f"/g/{group.id}/transactions")
    return {"expenses": created_expenses, "settlements": created_settlements, "skipped": skipped,
            "flagged": flagged}


def sample_statement(group: Group, members: list[GroupMember], me: GroupMember) -> str:
    """A synthetic wallet statement for demos (generic MFS CSV export layout). Not real data."""
    rng = random.Random(f"{group.id}:{local_now():%Y-%m-%d}")
    others = [m for m in members if m.id != me.id and m.status == "active"]
    now = local_now().replace(second=0, microsecond=0)

    def txn() -> str:
        return "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(10))

    def at(days: int, hour: int, minute: int) -> datetime:
        return (now - timedelta(days=days)).replace(hour=hour, minute=minute)

    rows: list[tuple[datetime, str, str, str, int]] = [
        (at(1, 20, 40), "Payment", "Kacchi Bhai", "Dinner for the group", -rng.choice([1450, 1680, 1820])),
        (at(2, 9, 15), "Payment", "Pathao", "Ride to campus", -rng.choice([210, 245, 280])),
        (at(3, 18, 5), "Payment", "Shwapno", "Groceries for the flat", -rng.choice([1260, 1540, 1880])),
        (at(4, 11, 30), "Bill Pay", "DESCO", "Electricity bill", -rng.choice([1640, 1780, 1920])),
        (at(4, 13, 10), "Mobile Recharge", "Grameenphone", "Recharge", -rng.choice([99, 149, 199])),
        (at(5, 21, 15), "Payment", "Foodpanda", "Biryani order", -rng.choice([960, 1120, 1340])),
        (at(6, 16, 45), "Payment", "Star Cineplex", "Movie tickets", -rng.choice([1600, 2000, 2400])),
        (at(7, 12, 20), "Cash Out", "Agent 01811-XXXXXX", "Cash out", -rng.choice([1000, 2000])),
        (at(8, 10, 0), "Add Money", "UCB Bank", "Add money from bank", rng.choice([5000, 8000])),
        (at(9, 19, 30), "Payment", "Aarong", "Panjabi", -rng.choice([1850, 2290])),
    ]
    if others:
        a = others[0]
        rows.append((at(2, 22, 5), "Send Money", f"{a.display_name} (01712-XXXXXX)",
                     "Paid back for the trip", -rng.choice([500, 750, 1000])))
        rows.append((at(5, 14, 50), "Received Money", f"{a.display_name} (01712-XXXXXX)",
                     "Snacks money", rng.choice([300, 450])))
    if len(others) > 1:
        b = others[1]
        rows.append((at(6, 10, 35), "Send Money", f"{b.display_name} (01913-XXXXXX)",
                     "My share of rent", -rng.choice([600, 900])))
    rows.append((at(3, 8, 0), "Send Money", "Ammu (01556-XXXXXX)", "Family", -1500))
    rows.sort(key=lambda r: r[0], reverse=True)
    lines = ["Date,Time,Transaction Type,To/From,Details,Amount (BDT),TrxID"]
    for when, kind, party, details, amount in rows:
        lines.append(f"{when:%d/%m/%Y},{when:%I:%M %p},{kind},{party},{details},{amount:.2f},{txn()}")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- payment requests
def _expire_if_due(pr: PaymentRequest) -> None:
    if pr.status == "pending" and utc_now() > pr.expires_at:
        pr.status = "expired"


def create_payment_request(db: Session, group: Group, payer: GroupMember, actor_user_id: str, purpose: str,
                           amount_paisa: int, payee_member_id: str | None = None, goal_id: str | None = None) -> PaymentRequest:
    if not get_settings().wallet_sandbox_enabled:
        raise WalletError("Wallet payments are not enabled on this server.")
    if payer.group_id != group.id or payer.status != "active":
        raise WalletError("Choose an active member of this group.")
    if purpose == "settlement":
        payee = db.get(GroupMember, payee_member_id) if payee_member_id else None
        if payee is None or payee.group_id != group.id or payee.status != "active" or payee.id == payer.id:
            raise WalletError("Choose another active member of this group to pay.")
        goal_id = None
    elif purpose == "goal_contribution":
        goal = db.get(Goal, goal_id) if goal_id else None
        if goal is None or goal.group_id != group.id or goal.status != "active":
            raise WalletError("Choose an active goal of this group.")
        payee_member_id = None
    else:
        raise WalletError("Unknown payment purpose.")
    if not 0 < amount_paisa <= MAX_AMOUNT_PAISA:
        raise WalletError("Enter an amount greater than zero.")
    pr = PaymentRequest(group_id=group.id, purpose=purpose, payer_member_id=payer.id, payee_member_id=payee_member_id,
                        goal_id=goal_id, amount_paisa=amount_paisa, reference=new_reference(), provider=SandboxWallet.name,
                        created_by_user_id=actor_user_id,
                        expires_at=utc_now() + timedelta(minutes=get_settings().wallet_request_ttl_minutes))
    db.add(pr)
    db.flush()
    return pr


def approve_mode(pr: PaymentRequest, payer: GroupMember | None, viewer_user_id: str | None) -> str | None:
    """Who may approve: the payer in their own wallet, or (sandbox only) the requester simulating a friend
    who is not on the app. Real wallets would deliver the request to that friend's phone instead."""
    if pr.status != "pending" or not viewer_user_id or payer is None:
        return None
    if payer.user_id == viewer_user_id:
        return "payer"
    if pr.provider == SandboxWallet.name and payer.user_id is None and pr.created_by_user_id == viewer_user_id:
        return "simulate_friend"
    return None


def payment_request_out(db: Session, pr: PaymentRequest, viewer_user_id: str | None = None) -> dict:
    _expire_if_due(pr)
    group = db.get(Group, pr.group_id)
    payer = db.get(GroupMember, pr.payer_member_id)
    payee = db.get(GroupMember, pr.payee_member_id) if pr.payee_member_id else None
    goal = db.get(Goal, pr.goal_id) if pr.goal_id else None
    return {
        "id": pr.id, "reference": pr.reference, "purpose": pr.purpose, "status": pr.status, "amount": pr.amount_paisa,
        "group_id": pr.group_id, "group_name": group.name if group else None,
        "payer_member_id": pr.payer_member_id, "payer_name": payer.display_name if payer else None,
        "payee_member_id": pr.payee_member_id, "payee_name": payee.display_name if payee else None,
        "goal_id": pr.goal_id, "goal_title": goal.title if goal else None,
        "provider": pr.provider, "is_sandbox": pr.provider == SandboxWallet.name,
        "provider_txn_id": pr.provider_txn_id, "result_id": pr.result_id,
        "created_at": pr.created_at.isoformat() + "Z", "expires_at": pr.expires_at.isoformat() + "Z",
        "completed_at": pr.completed_at.isoformat() + "Z" if pr.completed_at else None,
        "approve_as": approve_mode(pr, payer, viewer_user_id),
        "can_approve": approve_mode(pr, payer, viewer_user_id) is not None,
        "is_request": bool(payer and payer.user_id != pr.created_by_user_id),
        "checkout_url": f"/pay/{pr.id}",
    }


class EventRejected(ValueError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def apply_wallet_event(db: Session, event: dict) -> PaymentRequest:
    """Apply a verified wallet event. Idempotent: replaying the same success changes nothing."""
    kind = event.get("event")
    reference = str(event.get("reference") or "")
    pr = db.scalar(select(PaymentRequest).where(PaymentRequest.reference == reference))
    if pr is None:
        raise EventRejected(404, "Unknown payment reference.")
    txn_id = str(event.get("provider_txn_id") or "")[:64] or None
    if pr.status != "pending":
        if pr.status == "paid" and kind == "payment.succeeded" and txn_id == pr.provider_txn_id:
            return pr  # duplicate delivery of the same event
        raise EventRejected(409, f"This payment request is already {pr.status}.")
    _expire_if_due(pr)
    if pr.status == "expired":
        raise EventRejected(409, "This payment request has expired. Create a new one.")
    if kind in ("payment.failed", "payment.cancelled"):
        pr.status = "failed" if kind == "payment.failed" else "cancelled"
        pr.completed_at = utc_now()
        return pr
    if kind != "payment.succeeded":
        raise EventRejected(400, "Unsupported event type.")
    if event.get("currency", "BDT") != "BDT" or int(event.get("amount_paisa", -1)) != pr.amount_paisa:
        raise EventRejected(409, "Amount or currency does not match the payment request.")
    if not txn_id:
        raise EventRejected(400, "Missing provider transaction id.")
    # Atomic claim: only one concurrent delivery can move the request out of "pending". On Postgres the
    # row lock makes a simultaneous duplicate wait and then see 0 rows updated; SQLite serializes writes.
    claimed = db.execute(update(PaymentRequest).where(PaymentRequest.id == pr.id, PaymentRequest.status == "pending")
                         .values(status="processing", provider_txn_id=txn_id))
    if claimed.rowcount != 1:
        db.rollback()
        db.refresh(pr)
        if pr.status == "paid" and pr.provider_txn_id == txn_id:
            return pr
        raise EventRejected(409, f"This payment request is already {pr.status}.")
    group = db.get(Group, pr.group_id)
    payer = db.get(GroupMember, pr.payer_member_id)
    when = local_now()
    if pr.purpose == "settlement":
        payee = db.get(GroupMember, pr.payee_member_id)
        result = Settlement(group_id=pr.group_id, from_member_id=pr.payer_member_id, to_member_id=pr.payee_member_id,
                            amount_paisa=pr.amount_paisa, occurred_at=when,
                            note=f"Paid via wallet · {pr.reference} · TrxID {txn_id}",
                            created_by_user_id=pr.created_by_user_id)
        title = f"{payer.display_name} paid {payee.display_name} via wallet"
        link = f"/g/{pr.group_id}/balances"
    else:
        goal = db.get(Goal, pr.goal_id)
        result = GoalContribution(goal_id=pr.goal_id, member_id=pr.payer_member_id, amount_paisa=pr.amount_paisa,
                                  occurred_at=when, note=f"Saved via wallet · {pr.reference} · TrxID {txn_id}")
        title = f"{payer.display_name} added to “{goal.title}” via wallet"
        link = f"/g/{pr.group_id}/goals/{pr.goal_id}"
    db.add(result)
    db.flush()
    pr.status, pr.provider_txn_id, pr.result_id, pr.completed_at = "paid", txn_id, result.id, utc_now()
    group.data_version = Group.data_version + 1  # atomic in SQL: no lost updates
    payer_user = payer.user_id if payer else None
    notify_members(db, group, exclude_user_id=payer_user, kind="settlement", title=title,
                   body=f"৳{pr.amount_paisa / 100:,.2f} · reference {pr.reference}.", link=link)
    return pr


def sandbox_event(pr: PaymentRequest, approve: bool) -> dict:
    return {"event": "payment.succeeded" if approve else "payment.cancelled", "reference": pr.reference,
            "provider_txn_id": SandboxWallet.txn_id() if approve else None, "amount_paisa": pr.amount_paisa,
            "currency": "BDT", "occurred_at": utc_now().isoformat() + "Z"}
