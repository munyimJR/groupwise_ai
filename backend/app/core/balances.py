"""Balance engine (deterministic business logic — not AI).

net = paid upfront − own share of expenses + settlements sent − settlements received
  net > 0  → the member "gets" money back
  net < 0  → the member "owes" money
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExpenseRecord:
    payer_id: str
    amount: int
    shares: dict[str, int]


@dataclass(frozen=True)
class SettlementRecord:
    from_id: str
    to_id: str
    amount: int


@dataclass
class MemberBalance:
    member_id: str
    paid: int = 0
    share: int = 0
    settlements_sent: int = 0
    settlements_received: int = 0

    @property
    def net(self) -> int:
        return self.paid - self.share + self.settlements_sent - self.settlements_received


@dataclass
class BalanceSheet:
    members: dict[str, MemberBalance] = field(default_factory=dict)
    total_spent: int = 0

    def nets(self) -> dict[str, int]:
        return {mid: b.net for mid, b in self.members.items()}


def compute_balances(
    member_ids: Iterable[str],
    expenses: Iterable[ExpenseRecord],
    settlements: Iterable[SettlementRecord] = (),
) -> BalanceSheet:
    sheet = BalanceSheet(members={mid: MemberBalance(mid) for mid in member_ids})

    def get(mid: str) -> MemberBalance:
        # Members who left still keep their history in the ledger.
        if mid not in sheet.members:
            sheet.members[mid] = MemberBalance(mid)
        return sheet.members[mid]

    for exp in expenses:
        if sum(exp.shares.values()) != exp.amount:
            raise ValueError("Expense shares must sum to the expense amount.")
        sheet.total_spent += exp.amount
        get(exp.payer_id).paid += exp.amount
        for mid, share in exp.shares.items():
            get(mid).share += share

    for s in settlements:
        get(s.from_id).settlements_sent += s.amount
        get(s.to_id).settlements_received += s.amount

    if sum(sheet.nets().values()) != 0:  # invariant: money is conserved
        raise AssertionError("Balance sheet does not net to zero.")
    return sheet


def pairwise_debts(expenses: Iterable[ExpenseRecord], settlements: Iterable[SettlementRecord] = ()) -> dict[tuple[str, str], int]:
    """Net amount each debtor owes each creditor if nobody simplified anything.

    Returned as {(debtor, creditor): amount>0}. Used to show how many payments the
    simplification saves compared with settling every pair separately.
    """
    owed: dict[tuple[str, str], int] = defaultdict(int)
    for exp in expenses:
        for mid, share in exp.shares.items():
            if mid != exp.payer_id and share:
                owed[(mid, exp.payer_id)] += share
    for s in settlements:
        owed[(s.from_id, s.to_id)] -= s.amount

    result: dict[tuple[str, str], int] = {}
    seen: set[frozenset[str]] = set()
    for a, b in list(owed.keys()):
        pair = frozenset((a, b))
        if pair in seen or a == b:
            continue
        seen.add(pair)
        net = owed.get((a, b), 0) - owed.get((b, a), 0)
        if net > 0:
            result[(a, b)] = net
        elif net < 0:
            result[(b, a)] = -net
    return result
