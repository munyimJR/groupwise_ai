"""Behaviour-driven synthetic data generator.

Not random noise: every group is simulated from explicit, documented behaviour —
  * time patterns   — weekday lunches, Thu–Sat dinners (Bangladesh weekend = Fri/Sat),
                       month-start "allowance" effect, evening rides, late-night deliveries
  * trends          — e.g. weekend restaurant spending rising over the last 30 days
  * group behaviour — some members pay upfront far more often; members settle on different
                       cadences, producing real reimbursement delays
  * recurring bills — rent, utilities, internet on predictable days of the month
  * anomalies       — amount spikes, unusual hours, rare categories, duplicates (labelled)
  * goals           — groups that are on track and groups that are behind

All amounts are generated in taka and stored in paisa. The output is plain data so it can be
seeded into the database *and* used offline for model evaluation.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from ..core.splits import equal_split
from .catalog import CATALOG, MONTHS, PEOPLE

WEEKEND = {4, 5}  # Friday, Saturday


@dataclass
class MemberSpec:
    key: str
    name: str
    payer_weight: float = 1.0
    settle_every: tuple[int, int] = (2, 5)  # days between settling up
    settle_fraction: tuple[float, float] = (0.85, 1.0)
    color: str = "#0057B8"
    is_primary_user: bool = False


@dataclass
class PatternSpec:
    subcategory: str
    rate: float  # expected expenses per day before multipliers
    median: float  # typical amount in taka
    sigma: float = 0.35  # log-normal spread
    hours: tuple[tuple[float, float, float], ...] = ((12, 15, 1.0),)
    dow: dict[int, float] = field(default_factory=dict)  # Mon=0 … Sun=6
    participants: tuple[float, float] = (0.6, 1.0)
    month_start_mult: float = 1.0  # days 1–7 (allowance / salary week)
    month_end_mult: float = 1.0  # days 24+
    recent_days: int = 0  # trend window ending today
    recent_rate_mult: float = 1.0
    recent_amount_mult: float = 1.0
    window: tuple[int, int] | None = None  # (start_days_ago, end_days_ago) when the pattern is active
    templates: list[str] | None = None
    merchants: list[str] | None = None
    round_to: int = 10


@dataclass
class FixedExpense:
    days_ago: int
    hour: float
    subcategory: str
    amount: float
    description: str
    payer: str
    merchant: str | None = None
    participants: list[str] | None = None  # None = all members
    is_anomaly: bool = False
    anomaly_kind: str | None = None
    reviewed_valid: bool = False


@dataclass
class RecurringSpec:
    subcategory: str
    day_of_month: int
    amount: float
    payer: str
    description: str
    merchant: str | None = None
    jitter_pct: float = 0.0
    day_jitter: int = 1


@dataclass
class GoalSpec:
    title: str
    description: str
    target: float
    start_days_ago: int
    duration_days: int
    weekly_total: float  # average total contributed per week by the group
    contributor_weights: dict[str, float] | None = None
    weekly_noise: float = 0.35
    participation: float = 0.8  # chance each member contributes in a given week


@dataclass
class GroupScenario:
    key: str
    name: str
    description: str
    group_type: str
    members: list[MemberSpec]
    days: int
    seed: int
    patterns: list[PatternSpec] = field(default_factory=list)
    recurring: list[RecurringSpec] = field(default_factory=list)
    fixed: list[FixedExpense] = field(default_factory=list)
    goals: list[GoalSpec] = field(default_factory=list)
    settle_until_days_ago: int = 0  # stop settling after this point (leaves open balances)
    monthly_budget: float | None = None
    # Demo groups use systematic (low-variance) sampling of event counts so the designed behaviour
    # is visible whichever day the demo is opened; evaluation groups keep full Poisson noise.
    low_variance: bool = False


# ----------------------------------------------------------------------------- output types
@dataclass
class GenExpense:
    payer: str
    amount_paisa: int
    shares: dict[str, int]
    description: str
    merchant: str | None
    subcategory: str
    occurred_at: datetime
    payment_method: str
    is_anomaly: bool = False
    anomaly_kind: str | None = None
    reviewed_valid: bool = False


@dataclass
class GenSettlement:
    from_member: str
    to_member: str
    amount_paisa: int
    occurred_at: datetime


@dataclass
class GenContribution:
    member: str
    amount_paisa: int
    occurred_at: datetime


@dataclass
class GenGoal:
    spec: GoalSpec
    start: date
    deadline: date
    contributions: list[GenContribution]


@dataclass
class GeneratedGroup:
    scenario: GroupScenario
    expenses: list[GenExpense]
    settlements: list[GenSettlement]
    goals: list[GenGoal]


# ----------------------------------------------------------------------------- helpers
def _poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    l_, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= l_:
            return k
        k += 1


def _round_amount(value: float, step: int) -> float:
    if value >= 5000:
        step = max(step, 50)
    return max(step, round(value / step) * step)


def _pick_hour(rng: random.Random, hours: tuple[tuple[float, float, float], ...]) -> float:
    total = sum(w for _, _, w in hours)
    r = rng.random() * total
    for start, end, w in hours:
        if r <= w:
            return rng.uniform(start, end)
        r -= w
    return rng.uniform(hours[-1][0], hours[-1][1])


def _at(day: date, hour: float) -> datetime:
    hour = min(max(hour, 0.0), 23.99)
    h = int(hour)
    m = int((hour - h) * 60)
    return datetime(day.year, day.month, day.day, h, m)


def _describe(rng: random.Random, sub: str, templates: list[str] | None, merchants: list[str] | None) -> tuple[str, str | None]:
    spec = CATALOG[sub]
    tmpl = rng.choice(templates or spec["templates"])
    merchant = rng.choice(merchants or spec["merchants"]) if (merchants or spec["merchants"]) else None
    text = tmpl.format(m=merchant or "", month=rng.choice(MONTHS), person=rng.choice(PEOPLE)).strip()
    return text, (merchant if "{m}" in tmpl else None)


def _payment_method(rng: random.Random, amount: float) -> str:
    if amount < 300:
        return rng.choices(["cash", "mobile_wallet"], [0.6, 0.4])[0]
    if amount > 8000:
        return rng.choices(["bank_transfer", "card", "mobile_wallet"], [0.4, 0.2, 0.4])[0]
    return rng.choices(["mobile_wallet", "cash", "card"], [0.6, 0.25, 0.15])[0]


# ----------------------------------------------------------------------------- generation
def generate_group(sc: GroupScenario, today: datetime) -> GeneratedGroup:
    rng = random.Random(sc.seed)
    members = [m.key for m in sc.members]
    weights = {m.key: m.payer_weight for m in sc.members}
    end_day = today.date()
    start_day = end_day - timedelta(days=sc.days)
    expenses: list[GenExpense] = []

    def add_expense(payer: str, amount: float, parts: list[str], description: str, merchant: str | None,
                    sub: str, when: datetime, **kw) -> None:
        if when > today:
            return
        paisa = int(round(amount * 100))
        # Payer first so rounding remainders are absorbed predictably.
        ordered = [payer] + [p for p in parts if p != payer] if payer in parts else parts
        expenses.append(GenExpense(payer, paisa, equal_split(paisa, ordered), description, merchant, sub, when,
                                   _payment_method(rng, amount), **kw))

    # 1) behavioural patterns
    accumulators = [rng.random() for _ in sc.patterns]
    day = start_day
    while day <= end_day:
        days_ago = (end_day - day).days
        for p_idx, pat in enumerate(sc.patterns):
            if pat.window and not (pat.window[1] <= days_ago <= pat.window[0]):
                continue
            lam = pat.rate * pat.dow.get(day.weekday(), 1.0)
            if day.day <= 7:
                lam *= pat.month_start_mult
            elif day.day >= 24:
                lam *= pat.month_end_mult
            amount_mult = 1.0
            if pat.recent_days and days_ago < pat.recent_days:
                lam *= pat.recent_rate_mult
                amount_mult = pat.recent_amount_mult
            if sc.low_variance:
                accumulators[p_idx] += lam * rng.uniform(0.85, 1.15)
                count = int(accumulators[p_idx])
                accumulators[p_idx] -= count
            else:
                count = _poisson(rng, lam)
            for _ in range(count):
                lo, hi = pat.participants
                k = max(2, min(len(members), round(rng.uniform(lo, hi) * len(members))))
                parts = rng.sample(members, k)
                payer = rng.choices(parts, [weights[p] for p in parts])[0]
                amount = _round_amount(rng.lognormvariate(math.log(pat.median * amount_mult), pat.sigma)
                                       * (0.75 + 0.25 * k / len(members)), pat.round_to)
                text, merchant = _describe(rng, pat.subcategory, pat.templates, pat.merchants)
                add_expense(payer, amount, parts, text, merchant, pat.subcategory, _at(day, _pick_hour(rng, pat.hours)))
        # 2) recurring bills
        for rec in sc.recurring:
            target_day = min(rec.day_of_month, 28)
            if day.day == target_day:
                shift = rng.randint(-rec.day_jitter, rec.day_jitter) if rec.day_jitter else 0
                when_day = day + timedelta(days=shift)
                amount = _round_amount(rec.amount * (1 + rng.uniform(-rec.jitter_pct, rec.jitter_pct)), 10)
                desc = rec.description.format(month=MONTHS[when_day.month - 1])
                add_expense(rec.payer, amount, members, desc, rec.merchant, rec.subcategory,
                            _at(when_day, rng.uniform(10, 21)))
        day += timedelta(days=1)

    # 3) fixed one-off expenses (trip bookings) and labelled anomalies
    for fx in sc.fixed:
        when = _at(end_day - timedelta(days=fx.days_ago), fx.hour)
        add_expense(fx.payer, fx.amount, fx.participants or members, fx.description, fx.merchant, fx.subcategory, when,
                    is_anomaly=fx.is_anomaly, anomaly_kind=fx.anomaly_kind, reviewed_valid=fx.reviewed_valid)

    expenses.sort(key=lambda e: e.occurred_at)
    settlements = _simulate_settlements(sc, expenses, start_day, end_day, today, rng)
    goals = [_simulate_goal(g, members, end_day, today, rng) for g in sc.goals]
    return GeneratedGroup(sc, expenses, settlements, goals)


def _simulate_settlements(sc: GroupScenario, expenses: list[GenExpense], start_day: date, end_day: date,
                          today: datetime, rng: random.Random) -> list[GenSettlement]:
    """Members settle what they owe on their own cadence → realistic reimbursement delays."""
    owes: dict[tuple[str, str], int] = defaultdict(int)  # (debtor, creditor) → paisa, kept netted

    def add_debt(a: str, b: str, amt: int) -> None:
        reverse = owes.get((b, a), 0)
        if reverse >= amt:
            owes[(b, a)] = reverse - amt
        else:
            owes[(b, a)] = 0
            owes[(a, b)] += amt - reverse

    specs = {m.key: m for m in sc.members}
    next_settle = {m.key: start_day + timedelta(days=rng.randint(*m.settle_every)) for m in sc.members}
    settlements: list[GenSettlement] = []
    idx = 0
    day = start_day
    stop_day = end_day - timedelta(days=sc.settle_until_days_ago)
    while day <= end_day:
        while idx < len(expenses) and expenses[idx].occurred_at.date() <= day:
            e = expenses[idx]
            for mid, share in e.shares.items():
                if mid != e.payer and share:
                    add_debt(mid, e.payer, share)
            idx += 1
        if day <= stop_day:
            for key, spec in specs.items():
                if next_settle[key] != day:
                    continue
                for (debtor, creditor), amt in list(owes.items()):
                    if debtor != key or amt < 5000:  # ignore < ৳50
                        continue
                    pay = int(amt * rng.uniform(*spec.settle_fraction))
                    pay = max(5000, (pay // 1000) * 1000)  # round down to ৳10
                    pay = min(pay, amt)
                    when = _at(day, rng.uniform(19, 23))
                    if when > today:
                        continue
                    settlements.append(GenSettlement(key, creditor, pay, when))
                    owes[(debtor, creditor)] -= pay
                next_settle[key] = day + timedelta(days=rng.randint(*spec.settle_every))
        day += timedelta(days=1)
    return settlements


def _simulate_goal(g: GoalSpec, members: list[str], end_day: date, today: datetime, rng: random.Random) -> GenGoal:
    start = end_day - timedelta(days=g.start_days_ago)
    deadline = start + timedelta(days=g.duration_days)
    weights = g.contributor_weights or {m: 1.0 for m in members}
    contributions: list[GenContribution] = []
    week_start = start
    while week_start <= end_day:
        weekly = max(0.0, rng.gauss(g.weekly_total, g.weekly_total * g.weekly_noise))
        total_w = sum(weights.values())
        for member, w in weights.items():
            if rng.random() < g.participation:  # not everyone contributes every week
                amount = _round_amount(weekly * w / total_w / g.participation, 50)
                when = _at(week_start + timedelta(days=rng.randint(0, 6)), rng.uniform(18, 23))
                if when <= today and when.date() >= start:
                    contributions.append(GenContribution(member, int(amount * 100), when))
        week_start += timedelta(days=7)
    contributions.sort(key=lambda c: c.occurred_at)
    return GenGoal(g, start, deadline, contributions)


# ----------------------------------------------------------------------------- shared patterns
LUNCH_DOW = {6: 1.15, 0: 1.15, 1: 1.15, 2: 1.15, 3: 1.0, 4: 0.3, 5: 0.6}
WEEKEND_NIGHT_DOW = {3: 1.8, 4: 2.2, 5: 1.5, 6: 0.5, 0: 0.5, 1: 0.5, 2: 0.6}
CLASS_DAY_DOW = {6: 1.2, 0: 1.2, 1: 1.2, 2: 1.2, 3: 1.1, 4: 0.2, 5: 0.4}
LUNCH_H = ((12.5, 15.0, 1.0),)
DINNER_H = ((19.0, 22.5, 1.0),)
SNACK_H = ((10.5, 12.0, 0.4), (15.5, 19.0, 1.0))
RIDE_H = ((8.0, 10.0, 1.0), (17.0, 22.0, 1.2))
LATE_H = ((20.5, 23.9, 1.0),)
DAY_H = ((10.0, 20.0, 1.0),)

COLORS = ["#0057B8", "#E5A400", "#16A34A", "#DB2777", "#7C3AED", "#0EA5E9", "#EA580C", "#0D9488"]
