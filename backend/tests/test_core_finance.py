import random

import pytest

from app.core.balances import ExpenseRecord, SettlementRecord, compute_balances, pairwise_debts
from app.core.money import MoneyError, fmt_taka, to_paisa
from app.core.simplify import simplify_debts
from app.core.splits import SplitError, compute_split, equal_split, exact_split, percentage_split


def test_to_paisa_rounding_and_validation():
    assert to_paisa("850") == 85000
    assert to_paisa(10.005) == 1001
    assert to_paisa("1,200".replace(",", "")) == 120000
    with pytest.raises(MoneyError):
        to_paisa(0)
    with pytest.raises(MoneyError):
        to_paisa("abc")
    assert fmt_taka(825000) == "৳8,250"


def test_equal_split_distributes_remainder_exactly():
    shares = equal_split(100, ["a", "b", "c"])
    assert shares == {"a": 34, "b": 33, "c": 33}
    assert sum(shares.values()) == 100
    # duplicates are ignored
    assert equal_split(90, ["a", "a", "b"]) == {"a": 45, "b": 45}
    with pytest.raises(SplitError):
        equal_split(100, [])


def test_percentage_and_exact_splits():
    shares = percentage_split(100_00, {"a": 33.33, "b": 33.33, "c": 33.34})
    assert sum(shares.values()) == 100_00
    with pytest.raises(SplitError):
        percentage_split(100, {"a": 50, "b": 40})
    assert exact_split(500, {"a": 200, "b": 300}) == {"a": 200, "b": 300}
    with pytest.raises(SplitError):
        exact_split(500, {"a": 200, "b": 200})
    assert compute_split("equal", 10, ["x", "y"]) == {"x": 5, "y": 5}


def test_balances_basic_scenario():
    # A pays 900 for A,B,C. B pays 300 for B,C. C settles 300 to A.
    exps = [
        ExpenseRecord("A", 900, equal_split(900, ["A", "B", "C"])),
        ExpenseRecord("B", 300, equal_split(300, ["B", "C"])),
    ]
    sheet = compute_balances(["A", "B", "C"], exps, [SettlementRecord("C", "A", 300)])
    nets = sheet.nets()
    assert nets == {"A": 300, "B": -150, "C": -150}
    assert sheet.total_spent == 1200
    assert sum(nets.values()) == 0


def test_balances_reject_inconsistent_shares():
    with pytest.raises(ValueError):
        compute_balances(["A"], [ExpenseRecord("A", 100, {"A": 90})])


def test_simplify_settles_everyone_with_at_most_n_minus_1_transfers():
    rng = random.Random(7)
    for _ in range(300):
        n = rng.randint(2, 9)
        ids = [f"m{i}" for i in range(n)]
        exps = []
        for _ in range(rng.randint(1, 25)):
            payer = rng.choice(ids)
            parts = rng.sample(ids, rng.randint(1, n))
            amt = rng.randint(1, 500_000)
            exps.append(ExpenseRecord(payer, amt, equal_split(amt, parts)))
        nets = compute_balances(ids, exps).nets()
        transfers = simplify_debts(nets)
        nonzero = sum(1 for v in nets.values() if v != 0)
        assert len(transfers) <= max(nonzero - 1, 0)
        after = dict(nets)
        for t in transfers:
            assert t.amount > 0
            assert nets[t.from_id] < 0 < nets[t.to_id]
            after[t.from_id] += t.amount
            after[t.to_id] -= t.amount
        assert all(v == 0 for v in after.values())


def test_simplify_is_deterministic_and_rejects_unbalanced():
    nets = {"a": 500, "b": -200, "c": -300}
    assert simplify_debts(nets) == simplify_debts(dict(reversed(list(nets.items()))))
    with pytest.raises(ValueError):
        simplify_debts({"a": 1, "b": 0})


def test_pairwise_debts_net_out_reverse_directions():
    exps = [
        ExpenseRecord("A", 200, {"A": 100, "B": 100}),
        ExpenseRecord("B", 100, {"A": 50, "B": 50}),
    ]
    assert pairwise_debts(exps) == {("B", "A"): 50}
    assert pairwise_debts(exps, [SettlementRecord("B", "A", 50)]) == {}
