"""Scenario model for GroupWise inside a mobile wallet (for example a future upay integration).

    python research/business_case.py            # prints the scenario table (markdown)

Inputs live in business_case_assumptions.json. Only the student count is a cited fact; every other input is an
assumption that the survey, pilot or a partner A/B test replaces (see its "replaced_by"). The model outputs
volumes and customers, not revenue: fees, float income and acquisition costs are the wallet operator's own
numbers. Standard library only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

INPUTS = json.loads((Path(__file__).parent / "business_case_assumptions.json").read_text(encoding="utf-8"))
SCENARIOS = ("conservative", "base", "optimistic")


def model(a: dict, students: int) -> dict:
    users = students * a["adoption_share"]
    groups = users * a["groups_per_user"] / a["group_size"]
    settle_txns = users * a["settlements_per_user_month"] * a["wallet_settle_share"]
    return {
        "Active users": users,
        "Active groups": groups,
        "Shared spending organized per month (৳)": groups * a["expenses_per_group_month"] * a["avg_expense_taka"],
        "Pay-backs through the wallet per month": settle_txns,
        "Pay-back volume through the wallet per month (৳)": settle_txns * a["avg_settlement_taka"],
        "Balances held in goal pockets (৳)": groups * a["goal_group_share"] * a["avg_goal_taka"] * a["goal_balance_fraction"],
        "New wallet customers from group invites": groups * a["group_size"] * a["non_customer_members"] * a["invite_conversion"],
    }


def fmt(v: float) -> str:
    for unit, div in (("bn", 1e9), ("m", 1e6), ("k", 1e3)):
        if abs(v) >= div:
            return f"{v / div:,.1f}{unit}"
    return f"{v:,.0f}"


def table() -> str:
    students = INPUTS["facts"]["students"]["value"]
    results = {s: model({k: v[s] for k, v in INPUTS["assumptions"].items()}, students) for s in SCENARIOS}
    lines = ["| Output (per month unless noted) | Conservative | Base | Optimistic |", "|---|---|---|---|"]
    for key in results["base"]:
        lines.append(f"| {key} | " + " | ".join(fmt(results[s][key]) for s in SCENARIOS) + " |")
    lines += ["", "| Assumption | Conservative | Base | Optimistic | Replaced by |", "|---|---|---|---|---|"]
    for v in INPUTS["assumptions"].values():
        def show(x):
            return f"{x:.1%}" if isinstance(x, float) and x < 1 else f"{x:,}"
        lines.append(f"| {v['label']} | {show(v['conservative'])} | {show(v['base'])} | {show(v['optimistic'])} | {v['replaced_by']} |")
    lines.append(f"\nFact: {students:,} students — {INPUTS['facts']['students']['source']}.")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(table())
