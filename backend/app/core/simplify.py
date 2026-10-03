"""Debt simplification (deterministic algorithm — not AI).

Greedy minimum cash-flow: repeatedly match the largest creditor with the largest debtor.
Guarantees:
  * every member ends at exactly zero,
  * at most (n − 1) transfers for n members with non-zero balances,
  * no one pays more than they owe and no one receives more than they are owed.
Ties are broken by member id so results are reproducible.
"""
from __future__ import annotations

import heapq
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Transfer:
    from_id: str
    to_id: str
    amount: int


def simplify_debts(nets: Mapping[str, int]) -> list[Transfer]:
    if sum(nets.values()) != 0:
        raise ValueError("Balances must sum to zero.")

    creditors = [(-amount, mid) for mid, amount in nets.items() if amount > 0]
    debtors = [(amount, mid) for mid, amount in nets.items() if amount < 0]  # amount negative → most negative first
    heapq.heapify(creditors)
    heapq.heapify(debtors)

    transfers: list[Transfer] = []
    while creditors and debtors:
        neg_credit, creditor = heapq.heappop(creditors)
        debt, debtor = heapq.heappop(debtors)
        credit, owe = -neg_credit, -debt
        amount = min(credit, owe)
        transfers.append(Transfer(from_id=debtor, to_id=creditor, amount=amount))
        if credit > amount:
            heapq.heappush(creditors, (-(credit - amount), creditor))
        if owe > amount:
            heapq.heappush(debtors, (-(owe - amount), debtor))
    return transfers
