"""Expense taxonomy: category → subcategory → expense type, plus a discretionary flag.

Discretionary subcategories are the ones the goal planner and What-If simulator treat as
adjustable ("could be reduced"); essentials (rent, utilities, groceries…) are never suggested
as savings levers.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Subcategory:
    key: str
    category: str
    label: str
    expense_type: str
    discretionary: bool


_TAXONOMY: list[Subcategory] = [
    Subcategory("restaurant", "Food", "Restaurant", "Shared Meal", True),
    Subcategory("fast_food", "Food", "Fast Food", "Shared Meal", True),
    Subcategory("food_delivery", "Food", "Food Delivery", "Delivery Order", True),
    Subcategory("cafe_snacks", "Food", "Cafe & Snacks", "Snacks & Tea", True),
    Subcategory("supermarket", "Groceries", "Supermarket", "Household Groceries", False),
    Subcategory("fresh_market", "Groceries", "Bazaar & Fresh Market", "Household Groceries", False),
    Subcategory("ride_hailing", "Transport", "Ride-hailing", "Ride", False),
    Subcategory("rickshaw_cng", "Transport", "Rickshaw & CNG", "Ride", False),
    Subcategory("bus_train", "Transport", "Bus & Train", "Intercity Travel", False),
    Subcategory("fuel", "Transport", "Fuel", "Fuel", False),
    Subcategory("accommodation", "Travel", "Accommodation", "Stay", True),
    Subcategory("tours_activities", "Travel", "Tours & Activities", "Activity", True),
    Subcategory("flights", "Travel", "Flights", "Intercity Travel", True),
    Subcategory("rent", "Housing", "Rent", "Rent", False),
    Subcategory("household_supplies", "Housing", "Household Supplies", "Household Supplies", False),
    Subcategory("home_services", "Housing", "Home Services", "Household Service", False),
    Subcategory("electricity", "Utilities", "Electricity", "Utility Bill", False),
    Subcategory("gas", "Utilities", "Gas", "Utility Bill", False),
    Subcategory("water", "Utilities", "Water", "Utility Bill", False),
    Subcategory("internet", "Utilities", "Internet", "Utility Bill", False),
    Subcategory("mobile_recharge", "Utilities", "Mobile Recharge", "Recharge", False),
    Subcategory("movies", "Entertainment", "Movies", "Outing", True),
    Subcategory("gaming", "Entertainment", "Gaming", "Outing", True),
    Subcategory("events", "Entertainment", "Events & Concerts", "Event", True),
    Subcategory("subscriptions", "Entertainment", "Subscriptions", "Subscription", True),
    Subcategory("books_stationery", "Education", "Books & Stationery", "Study Material", False),
    Subcategory("printing", "Education", "Printing & Photocopy", "Study Material", False),
    Subcategory("course_fees", "Education", "Course & Exam Fees", "Fees", False),
    Subcategory("clothing", "Shopping", "Clothing", "Purchase", True),
    Subcategory("electronics", "Shopping", "Electronics", "Purchase", True),
    Subcategory("gifts", "Shopping", "Gifts", "Gift", True),
    Subcategory("pharmacy", "Health", "Pharmacy", "Medical", False),
    Subcategory("doctor", "Health", "Doctor & Diagnostics", "Medical", False),
    Subcategory("other", "Other", "Other", "Other", False),
]

SUBCATEGORIES: dict[str, Subcategory] = {s.key: s for s in _TAXONOMY}
CATEGORIES: list[str] = list(dict.fromkeys(s.category for s in _TAXONOMY))
DISCRETIONARY_CATEGORIES = {"Food", "Entertainment", "Shopping", "Travel"}

CATEGORY_COLORS = {
    "Food": "#F59E0B",
    "Groceries": "#16A34A",
    "Transport": "#0057B8",
    "Travel": "#0EA5E9",
    "Housing": "#7C3AED",
    "Utilities": "#64748B",
    "Entertainment": "#DB2777",
    "Education": "#0D9488",
    "Shopping": "#EA580C",
    "Health": "#DC2626",
    "Other": "#94A3B8",
}


def get_subcategory(key: str) -> Subcategory:
    return SUBCATEGORIES.get(key, SUBCATEGORIES["other"])


def taxonomy_payload() -> list[dict]:
    out: dict[str, dict] = {}
    for s in _TAXONOMY:
        cat = out.setdefault(s.category, {"category": s.category, "color": CATEGORY_COLORS[s.category], "subcategories": []})
        cat["subcategories"].append(
            {"key": s.key, "label": s.label, "expense_type": s.expense_type, "discretionary": s.discretionary}
        )
    return list(out.values())
