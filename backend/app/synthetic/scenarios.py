"""Demo scenarios (seeded for every demo sandbox) and randomized evaluation scenarios.

The demo groups are designed so that each AI feature has something real to find — but the
numbers shown in the product are always *computed* from the generated transactions, never
hard-coded. Evaluation scenarios use different seeds and jittered parameters and are never
seeded into the product.
"""
from __future__ import annotations

import random

from .generator import (
    CLASS_DAY_DOW,
    COLORS,
    DAY_H,
    DINNER_H,
    LATE_H,
    LUNCH_DOW,
    LUNCH_H,
    RIDE_H,
    SNACK_H,
    WEEKEND_NIGHT_DOW,
    FixedExpense,
    GoalSpec,
    GroupScenario,
    MemberSpec,
    PatternSpec,
    RecurringSpec,
)

PRIMARY = "you"  # the signed-in demo user


def friends_squad() -> GroupScenario:
    members = [
        MemberSpec(PRIMARY, "Ayaan Rahman", 1.2, (3, 5), (0.9, 1.0), COLORS[0], is_primary_user=True),
        MemberSpec("rafi", "Rafi Ahmed", 3.6, (3, 6), (0.95, 1.0), COLORS[1]),
        MemberSpec("nusrat", "Nusrat Jahan", 1.0, (1, 2), (0.95, 1.0), COLORS[2]),
        MemberSpec("tahsin", "Tahsin Karim", 0.6, (7, 11), (0.7, 0.9), COLORS[3]),
        MemberSpec("mitu", "Mitu Akter", 0.45, (4, 6), (0.85, 1.0), COLORS[4]),
    ]
    patterns = [
        PatternSpec("restaurant", 0.55, 850, 0.32, LUNCH_H, LUNCH_DOW, (0.6, 1.0), month_start_mult=1.15,
                    month_end_mult=0.85,
                    templates=["Lunch at {m}", "{m} lunch for everyone", "Kacchi lunch", "Tehari lunch",
                               "Bhuna khichuri lunch", "Lunch with friends", "Biryani at {m}"]),
        PatternSpec("restaurant", 0.30, 1800, 0.30, DINNER_H, {3: 2.0, 4: 2.4, 5: 1.6, 6: 0.3, 0: 0.3, 1: 0.3, 2: 0.4},
                    (0.8, 1.0), month_start_mult=1.2, recent_days=30, recent_rate_mult=1.45, recent_amount_mult=1.1,
                    templates=["Dinner at {m}", "{m} dinner", "Group dinner at {m}", "Weekend dinner",
                               "Buffet at {m}", "Thai food dinner", "Set menu dinner"]),
        PatternSpec("fast_food", 0.18, 1100, 0.38, DINNER_H, WEEKEND_NIGHT_DOW, (0.6, 1.0)),
        PatternSpec("food_delivery", 0.10, 800, 0.35, LATE_H, {4: 1.4, 5: 1.4}, (0.4, 0.8)),
        PatternSpec("cafe_snacks", 0.85, 220, 0.42, SNACK_H, CLASS_DAY_DOW, (0.4, 1.0), month_end_mult=0.9),
        PatternSpec("ride_hailing", 0.42, 240, 0.38, RIDE_H, CLASS_DAY_DOW, (0.4, 0.8)),
        PatternSpec("rickshaw_cng", 0.32, 110, 0.35, RIDE_H, CLASS_DAY_DOW, (0.4, 0.6)),
        PatternSpec("printing", 0.12, 200, 0.45, DAY_H, CLASS_DAY_DOW, (0.6, 1.0)),
        PatternSpec("books_stationery", 0.04, 600, 0.4, DAY_H, CLASS_DAY_DOW, (0.6, 1.0)),
        PatternSpec("movies", 0.05, 1700, 0.25, ((15, 21, 1.0),), {4: 2.0, 5: 1.6}, (0.6, 1.0)),
        PatternSpec("gaming", 0.05, 850, 0.35, ((16, 22, 1.0),), {3: 1.5, 4: 1.5}, (0.4, 0.8)),
        PatternSpec("events", 0.03, 2000, 0.3, ((14, 20, 1.0),), {}, (0.8, 1.0)),
        PatternSpec("gifts", 0.02, 1400, 0.3, ((17, 21, 1.0),), {}, (0.8, 1.0)),
    ]
    fixed = [
        # Main demo anomaly: plausible-but-unusual expense the group may confirm as valid.
        FixedExpense(5, 18.5, "events", 16500, "Sound system rental for freshers' event", "rafi", None,
                     is_anomaly=True, anomaly_kind="amount"),
        FixedExpense(17, 3.2, "food_delivery", 4200, "Foodpanda late night order", "tahsin", "Foodpanda",
                     participants=[PRIMARY, "tahsin", "rafi"], is_anomaly=True, anomaly_kind="time"),
        FixedExpense(11, 21.1, "restaurant", 2340, "Dinner at Star Kabab", PRIMARY, "Star Kabab",
                     participants=[PRIMARY, "rafi", "nusrat", "tahsin"]),
        FixedExpense(11, 21.15, "restaurant", 2340, "Dinner at Star Kabab", PRIMARY, "Star Kabab",
                     participants=[PRIMARY, "rafi", "nusrat", "tahsin"], is_anomaly=True, anomaly_kind="duplicate"),
        FixedExpense(70, 16.0, "electronics", 9800, "Laptop repair for project laptop", "nusrat", "Ryans Computers",
                     is_anomaly=True, anomaly_kind="category", reviewed_valid=True),
    ]
    goals = [
        GoalSpec("Cox's Bazar Trip", "Winter trip for the whole squad — bus, hotel and food for 3 nights.",
                 40000, start_days_ago=45, duration_days=120, weekly_total=1850, weekly_noise=0.12, participation=0.9,
                 contributor_weights={PRIMARY: 1.2, "rafi": 1.3, "nusrat": 1.0, "tahsin": 0.7, "mitu": 0.8}),
    ]
    return GroupScenario("squad", "DIU CSE Squad", "Five CSE classmates sharing lunches, rides, outings and a trip fund.",
                         "friends", members, days=150, seed=20261, patterns=patterns, fixed=fixed, goals=goals,
                         monthly_budget=45000, low_variance=True)


def roommates_flat() -> GroupScenario:
    members = [
        MemberSpec(PRIMARY, "Ayaan Rahman", 1.0, (3, 6), (0.9, 1.0), COLORS[0], is_primary_user=True),
        MemberSpec("sakib", "Sakib Hasan", 1.3, (2, 4), (0.95, 1.0), COLORS[5]),
        MemberSpec("farhan", "Farhan Kabir", 1.0, (2, 5), (0.9, 1.0), COLORS[6]),
        MemberSpec("imran", "Imran Hossain", 0.8, (7, 12), (0.75, 0.95), COLORS[7]),
    ]
    patterns = [
        PatternSpec("supermarket", 0.32, 950, 0.3, DAY_H, {4: 1.6, 5: 1.4}, (1.0, 1.0), month_start_mult=1.3),
        PatternSpec("fresh_market", 0.42, 480, 0.3, ((7, 11, 1.0), (17, 20, 0.6)), {4: 2.5, 5: 1.2}, (1.0, 1.0)),
        PatternSpec("household_supplies", 0.05, 450, 0.4, DAY_H, {}, (1.0, 1.0)),
        PatternSpec("food_delivery", 0.14, 850, 0.35, LATE_H, {3: 1.5, 4: 1.5}, (0.5, 1.0)),
        PatternSpec("cafe_snacks", 0.12, 200, 0.4, SNACK_H, {}, (0.5, 1.0)),
    ]
    recurring = [
        RecurringSpec("rent", 2, 28000, "sakib", "Flat rent {month}", None, 0.0, 1),
        RecurringSpec("home_services", 2, 3000, PRIMARY, "Bua salary {month}", None, 0.0, 1),
        RecurringSpec("internet", 5, 1200, "farhan", "Link3 wifi bill", "Link3", 0.0, 1),
        RecurringSpec("gas", 8, 1080, "sakib", "Titas gas bill {month}", "Titas Gas", 0.0, 2),
        RecurringSpec("electricity", 11, 1750, PRIMARY, "DESCO prepaid recharge", "DESCO", 0.15, 2),
        RecurringSpec("water", 14, 600, "imran", "WASA water bill", "Dhaka WASA", 0.05, 2),
    ]
    fixed = [
        FixedExpense(9, 13.0, "electricity", 6400, "DESCO prepaid recharge", "farhan", "DESCO",
                     is_anomaly=True, anomaly_kind="amount"),
    ]
    goals = [
        GoalSpec("Emergency Fund", "A shared buffer for repairs, medical needs or a late rent month.",
                 20000, start_days_ago=60, duration_days=120, weekly_total=1300, weekly_noise=0.12, participation=0.9),
    ]
    return GroupScenario("flat", "Mirpur Flat 7C", "Four roommates sharing rent, bills and groceries.", "roommates",
                         members, days=150, seed=20262, patterns=patterns, recurring=recurring, fixed=fixed,
                         goals=goals, monthly_budget=60000, low_variance=True)


def sajek_trip() -> GroupScenario:
    members = [
        MemberSpec(PRIMARY, "Ayaan Rahman", 1.0, (6, 9), (0.5, 0.8), COLORS[0], is_primary_user=True),
        MemberSpec("rafi", "Rafi Ahmed", 1.4, (5, 8), (0.6, 0.9), COLORS[1]),
        MemberSpec("nusrat", "Nusrat Jahan", 1.0, (4, 6), (0.7, 1.0), COLORS[2]),
        MemberSpec("tahsin", "Tahsin Karim", 0.9, (12, 20), (0.5, 0.7), COLORS[3]),
        MemberSpec("riya", "Riya Das", 1.0, (6, 9), (0.6, 0.9), COLORS[5]),
        MemberSpec("sakib", "Sakib Hasan", 1.1, (7, 10), (0.5, 0.8), COLORS[6]),
    ]
    trip = (41, 38)  # active between 41 and 38 days ago
    patterns = [
        PatternSpec("restaurant", 2.4, 2200, 0.3, ((8, 10, 0.8), (13, 15, 1.0), (20, 22, 1.0)), {}, (0.8, 1.0),
                    window=trip, templates=["Lunch at {m}", "Dinner at {m}", "Breakfast at {m}", "BBQ dinner"],
                    merchants=["Sajek Food Corner", "Megh Punji Restaurant", "Runmoy Restaurant", "Chander Bari"]),
        PatternSpec("cafe_snacks", 1.5, 380, 0.4, SNACK_H, {}, (0.6, 1.0), window=trip),
        PatternSpec("tours_activities", 0.8, 1200, 0.4, DAY_H, {}, (0.8, 1.0), window=trip,
                    templates=["Entry tickets", "Waterfall entry fee", "Tour guide fee", "Trekking guide"]),
    ]
    fixed = [
        FixedExpense(42, 21.0, "bus_train", 9600, "Shyamoli bus tickets Dhaka to Khagrachari", "rafi",
                     "Shyamoli Paribahan"),
        FixedExpense(41, 9.0, "tours_activities", 7500, "Chander gari rent day 1", "sakib", "Chander Gari"),
        FixedExpense(41, 15.0, "accommodation", 14000, "Resort booking 2 nights at Megh Machang", "nusrat",
                     "Megh Machang"),
        FixedExpense(39, 9.0, "tours_activities", 7500, "Chander gari rent day 3", PRIMARY, "Chander Gari"),
        FixedExpense(38, 20.0, "bus_train", 9600, "Return bus tickets Khagrachari to Dhaka", "tahsin",
                     "Shyamoli Paribahan"),
        FixedExpense(40, 17.0, "clothing", 3600, "Matching t-shirts for the tour", "riya", None),
    ]
    return GroupScenario("trip", "Sajek Valley Tour", "Four-day trip to Sajek — six friends, one shared wallet.",
                         "trip", members, days=45, seed=20263, patterns=patterns, fixed=fixed,
                         settle_until_days_ago=30, low_variance=True)


def demo_scenarios() -> list[GroupScenario]:
    return [friends_squad(), roommates_flat(), sajek_trip()]


# ----------------------------------------------------------------------------- evaluation
ANOMALY_KINDS = ("amount", "time", "category", "duplicate")


def eval_scenario(seed: int) -> GroupScenario:
    """A jittered friends- or roommates-style group with randomly injected, labelled anomalies.
    Uses seeds disjoint from the demo scenarios."""
    rng = random.Random(10_000 + seed)
    base = friends_squad() if rng.random() < 0.6 else roommates_flat()
    base.seed = 50_000 + seed
    base.key = f"eval-{seed}"
    base.low_variance = False  # evaluation keeps full sampling noise
    base.days = rng.randint(110, 180)
    base.fixed = []  # drop demo anomalies; inject fresh ones below
    for p in base.patterns:
        p.rate *= rng.uniform(0.7, 1.3)
        p.median *= rng.uniform(0.8, 1.25)
        p.recent_days = 0
    for r in base.recurring:
        r.amount *= rng.uniform(0.85, 1.15)
    n_members = len(base.members)
    keep = rng.randint(max(3, n_members - 1), n_members)
    base.members = base.members[:keep]
    keys = [m.key for m in base.members]
    base.recurring = [r for r in base.recurring if r.payer in keys]

    common = [p for p in base.patterns if p.rate >= 0.1] or base.patterns
    used = {p.subcategory for p in base.patterns} | {r.subcategory for r in base.recurring}
    rare_pool = [s for s in ("electronics", "flights", "course_fees", "doctor", "clothing") if s not in used]
    for _ in range(rng.randint(4, 8)):
        kind = rng.choice(ANOMALY_KINDS)
        days_ago = rng.randint(1, base.days - 20)
        payer = rng.choice(keys)
        if kind == "amount":
            p = rng.choice(common)
            fx = FixedExpense(days_ago, rng.uniform(11, 21), p.subcategory, round(p.median * rng.uniform(5, 10), -1),
                              f"{p.subcategory.replace('_', ' ')} expense", payer, is_anomaly=True, anomaly_kind=kind)
        elif kind == "time":
            p = rng.choice(common)
            fx = FixedExpense(days_ago, rng.uniform(2.0, 4.5), p.subcategory, round(p.median * rng.uniform(2.5, 4), -1),
                              f"{p.subcategory.replace('_', ' ')} late night", payer, is_anomaly=True,
                              anomaly_kind=kind)
        elif kind == "category" and rare_pool:
            sub = rng.choice(rare_pool)
            fx = FixedExpense(days_ago, rng.uniform(11, 20), sub, round(rng.uniform(6000, 15000), -1),
                              f"{sub.replace('_', ' ')} purchase", payer, is_anomaly=True, anomaly_kind="category")
        else:
            p = rng.choice(common)
            amount = round(p.median * rng.uniform(0.8, 1.6), -1)
            hour = rng.uniform(12, 21)
            base.fixed.append(FixedExpense(days_ago, hour, p.subcategory, amount, "duplicate source", payer))
            fx = FixedExpense(days_ago, hour + rng.uniform(0.02, 0.15), p.subcategory, amount, "duplicate source",
                              payer, is_anomaly=True, anomaly_kind="duplicate")
        base.fixed.append(fx)
    return base
