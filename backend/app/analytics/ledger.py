"""Balances & settle-up plan for a group snapshot (deterministic business logic)."""
from __future__ import annotations

from ..core.balances import ExpenseRecord, SettlementRecord, compute_balances, pairwise_debts
from ..core.simplify import simplify_debts
from ..services.snapshot import GroupSnapshot, memo


def balances(snap: GroupSnapshot) -> dict:
    def compute() -> dict:
        exps = [ExpenseRecord(e.payer_id, e.amount, e.shares) for e in snap.expenses]
        sets = [SettlementRecord(s.from_id, s.to_id, s.amount) for s in snap.settlements]
        sheet = compute_balances([m.id for m in snap.members], exps, sets)
        transfers = simplify_debts(sheet.nets())
        naive = pairwise_debts(exps, sets)
        members = []
        for m in snap.members:
            b = sheet.members[m.id]
            members.append({
                "member_id": m.id, "name": m.name, "color": m.color, "status": m.status,
                "paid": b.paid, "share": b.share, "settlements_sent": b.settlements_sent,
                "settlements_received": b.settlements_received, "net": b.net,
                "direction": "gets" if b.net > 0 else ("owes" if b.net < 0 else "settled"),
            })
        members.sort(key=lambda r: -r["net"])
        return {
            "total_spent": sheet.total_spent,
            "members": members,
            "transfers": [{"from_member_id": t.from_id, "from_name": snap.member_name(t.from_id),
                           "to_member_id": t.to_id, "to_name": snap.member_name(t.to_id), "amount": t.amount}
                          for t in transfers],
            "naive_transfer_count": len(naive),
            "simplified_transfer_count": len(transfers),
            "outstanding_total": sum(t.amount for t in transfers),
            "method": "Greedy minimum cash-flow (deterministic). Not AI.",
        }

    return memo(snap, "balances", compute)
