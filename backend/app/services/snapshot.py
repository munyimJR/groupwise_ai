"""Loads a group's financial state into plain dataclasses for analytics/ML.

Every analytics result is derived from this snapshot, which is read straight from the database
and cached per (group_id, data_version). Any financial mutation bumps data_version, so cached
insights can never go stale.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import local_now
from ..ml.anomaly import FLAG_THRESHOLD
from ..models import Expense, ExpenseSplit, Goal, GoalContribution, Group, GroupMember, Settlement


@dataclass
class MemberInfo:
    id: str
    name: str
    user_id: str | None
    role: str
    status: str
    color: str


@dataclass
class ExpenseInfo:
    id: str
    payer_id: str
    amount: int
    description: str
    merchant: str | None
    category: str
    subcategory: str
    expense_type: str
    occurred_at: datetime
    shares: dict[str, int]
    anomaly_score: float | None
    anomaly_status: str
    anomaly_reasons: list | None
    category_source: str

    @property
    def is_one_off(self) -> bool:
        """Unusual expenses excluded from pattern models (unless a person said it's normal)."""
        return (self.anomaly_score or 0) >= FLAG_THRESHOLD and self.anomaly_status != "dismissed"


@dataclass
class SettlementInfo:
    id: str
    from_id: str
    to_id: str
    amount: int
    occurred_at: datetime


@dataclass
class ContributionInfo:
    member_id: str
    amount: int
    occurred_at: datetime


@dataclass
class GoalInfo:
    id: str
    title: str
    description: str | None
    target: int
    start_date: date
    deadline: date
    status: str
    created_at: datetime
    contributions: list[ContributionInfo] = field(default_factory=list)

    @property
    def saved(self) -> int:
        return sum(c.amount for c in self.contributions)


@dataclass
class GroupSnapshot:
    group_id: str
    name: str
    group_type: str
    data_version: int
    monthly_budget: int | None
    members: list[MemberInfo]
    expenses: list[ExpenseInfo]
    settlements: list[SettlementInfo]
    goals: list[GoalInfo]
    as_of: datetime
    cache: dict[str, Any] = field(default_factory=dict)

    @property
    def active_members(self) -> list[MemberInfo]:
        return [m for m in self.members if m.status == "active"]

    def member_name(self, member_id: str) -> str:
        for m in self.members:
            if m.id == member_id:
                return m.name
        return "Former member"

    def member_for_user(self, user_id: str) -> MemberInfo | None:
        for m in self.members:
            if m.user_id == user_id:
                return m
        return None


def load_snapshot_uncached(db: Session, group: Group) -> GroupSnapshot:
    members = [MemberInfo(m.id, m.display_name, m.user_id, m.role, m.status, m.avatar_color)
               for m in db.scalars(select(GroupMember).where(GroupMember.group_id == group.id).order_by(GroupMember.joined_at))]
    rows = db.execute(
        select(Expense).where(Expense.group_id == group.id, Expense.is_deleted.is_(False)).order_by(Expense.occurred_at)
    ).scalars().all()
    shares: dict[str, dict[str, int]] = {}
    if rows:
        for sp in db.execute(
            select(ExpenseSplit.expense_id, ExpenseSplit.member_id, ExpenseSplit.share_paisa)
            .join(Expense, Expense.id == ExpenseSplit.expense_id)
            .where(Expense.group_id == group.id, Expense.is_deleted.is_(False))
        ):
            shares.setdefault(sp.expense_id, {})[sp.member_id] = sp.share_paisa
    expenses = [ExpenseInfo(e.id, e.payer_member_id, e.amount_paisa, e.description, e.merchant, e.category, e.subcategory,
                            e.expense_type, e.occurred_at, shares.get(e.id, {}), e.anomaly_score, e.anomaly_status,
                            e.anomaly_reasons, e.category_source) for e in rows]
    settlements = [SettlementInfo(s.id, s.from_member_id, s.to_member_id, s.amount_paisa, s.occurred_at)
                   for s in db.scalars(select(Settlement).where(Settlement.group_id == group.id).order_by(Settlement.occurred_at))]
    goals: list[GoalInfo] = []
    goal_rows = db.scalars(select(Goal).where(Goal.group_id == group.id).order_by(Goal.created_at)).all()
    if goal_rows:
        contribs: dict[str, list[ContributionInfo]] = {}
        for c in db.scalars(select(GoalContribution).where(GoalContribution.goal_id.in_([g.id for g in goal_rows]))
                            .order_by(GoalContribution.occurred_at)):
            contribs.setdefault(c.goal_id, []).append(ContributionInfo(c.member_id, c.amount_paisa, c.occurred_at))
        goals = [GoalInfo(g.id, g.title, g.description, g.target_paisa, g.start_date, g.deadline, g.status, g.created_at,
                          contribs.get(g.id, [])) for g in goal_rows]
    return GroupSnapshot(group.id, group.name, group.group_type, group.data_version, group.monthly_budget_paisa, members,
                         expenses, settlements, goals, local_now())


_cache: OrderedDict[tuple[str, int, str], GroupSnapshot] = OrderedDict()
_lock = threading.Lock()
_MAX = 64


def load_snapshot(db: Session, group: Group) -> GroupSnapshot:
    # Results are keyed by data version *and* local date so "today"-relative analytics roll over.
    key = (group.id, group.data_version, local_now().date().isoformat())
    with _lock:
        snap = _cache.get(key)
        if snap is not None:
            _cache.move_to_end(key)
            return snap
    snap = load_snapshot_uncached(db, group)
    with _lock:
        _cache[key] = snap
        while len(_cache) > _MAX:
            _cache.popitem(last=False)
    return snap


def memo(snap: GroupSnapshot, key: str, fn):
    """Per-snapshot memoization for expensive analyses."""
    if key not in snap.cache:
        snap.cache[key] = fn()
    return snap.cache[key]
