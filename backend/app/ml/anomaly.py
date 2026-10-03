"""AI Feature 3 — Unusual expense detection (hybrid, explainable).

Each expense is compared with the *group's own* history using several evidence signals:

  signal              method                                                  weight
  ------------------  ------------------------------------------------------  ------
  amount_peer         robust z-score of log-amount vs. the same subcategory     0.85
                      (falls back to category when the subcategory is new)
  amount_group        robust z-score vs. all of the group's expenses            0.60
  isolation           Isolation Forest over amount, peer z-score, rarity,       0.50
                      time-of-day, weekday and party size
  time                night-time expense in a group that rarely spends at night 0.60
  rare_category       large expense in a category the group almost never uses   0.55
  duplicate           same amount + merchant/description within 30 minutes      0.90

Signals are combined with a noisy-OR — score = 1 − Π(1 − wᵢ·sᵢ) — so one strong signal or
several moderate ones raise the score. Every flagged expense carries the human-readable
reasons that produced it. Expenses are never blocked: the group reviews and decides.
"""
from __future__ import annotations

import math
from bisect import bisect_left
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sklearn.ensemble import IsolationForest

from ..core.money import fmt_taka
from .taxonomy import get_subcategory

MODEL_NAME = "anomaly-hybrid"
MODEL_VERSION = "iforest-robust-1.2"
FLAG_THRESHOLD = 0.6
MIN_HISTORY_FOR_FOREST = 25
MIN_PEER_SUB = 4  # recurring bills have few but very consistent occurrences
MIN_PEER_CAT = 8
WEIGHTS = {"amount_peer": 0.85, "amount_group": 0.60, "isolation": 0.50, "time": 0.60, "rare_category": 0.55,
           "duplicate": 0.90}
MAD_FLOOR = 0.12  # in log space (~12%) so near-constant bills don't explode the z-score


@dataclass
class Txn:
    id: str
    amount: int  # paisa
    category: str
    subcategory: str
    occurred_at: datetime
    n_participants: int
    merchant: str | None = None
    description: str = ""


@dataclass
class _Stats:
    med: float
    mad: float
    n: int
    p10: float
    p90: float

    def z(self, log_amount: float) -> float:
        return (log_amount - self.med) / self.mad


def _stats(raw: list[int]) -> _Stats:
    arr = np.array(raw, dtype=float)
    logs = np.log(arr)
    med = float(np.median(logs))
    # Small samples get a wider floor so a handful of identical bills can't over-react.
    mad = max(float(np.median(np.abs(logs - med))) * 1.4826, MAD_FLOOR + 0.3 / len(raw))
    return _Stats(med, mad, len(raw), float(np.percentile(arr, 10)), float(np.percentile(arr, 90)))


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


class GroupAnomalyModel:
    """Fitted on one group's history; scores any expense of that group."""

    def __init__(self, history: list[Txn], n_members: int):
        self.history = history
        self.ids = {t.id for t in history}
        self.n_members = max(n_members, 1)
        self.n = len(history)
        sub_raw: dict[str, list[int]] = defaultdict(list)
        cat_raw: dict[str, list[int]] = defaultdict(list)
        for t in history:
            sub_raw[t.subcategory].append(t.amount)
            cat_raw[t.category].append(t.amount)
        self.sub_raw, self.cat_raw = sub_raw, cat_raw
        self.sub_stats = {k: _stats(v) for k, v in sub_raw.items() if len(v) >= MIN_PEER_SUB}
        self.cat_stats = {k: _stats(v) for k, v in cat_raw.items() if len(v) >= MIN_PEER_CAT}
        self._loo_cache: dict[tuple[str, str, int], _Stats | None] = {}
        self.cat_counts = Counter(t.category for t in history)
        self.sorted_amounts = sorted(t.amount for t in history)
        self.group_stats = _stats([t.amount for t in history]) if self.n >= 10 else None
        self.night_count = sum(1 for t in history if t.occurred_at.hour < 6)
        self.by_amount: dict[int, list[Txn]] = defaultdict(list)
        for t in history:
            self.by_amount[t.amount].append(t)
        self.forest: IsolationForest | None = None
        self.forest_train_scores: np.ndarray | None = None
        if self.n >= MIN_HISTORY_FOR_FOREST:
            X = self._feature_matrix(history)
            self.forest = IsolationForest(n_estimators=150, random_state=42, contamination="auto").fit(X)
            self.forest_train_scores = np.sort(-self.forest.score_samples(X))

    # ------------------------------------------------------------------ features
    def _peer(self, t: Txn, leave_one_out: bool = False) -> tuple[_Stats | None, str]:
        """Peer statistics for the expense; leave-one-out when it is part of the fitted history."""
        for level, key, raw, minimum in (("subcategory", t.subcategory, self.sub_raw, MIN_PEER_SUB),
                                         ("category", t.category, self.cat_raw, MIN_PEER_CAT)):
            values = raw.get(key, [])
            if not leave_one_out:
                if len(values) >= minimum:
                    return (self.sub_stats if level == "subcategory" else self.cat_stats)[key], level
                continue
            if len(values) - 1 >= minimum:
                cache_key = (level, key, t.amount)
                if cache_key not in self._loo_cache:
                    rest = list(values)
                    rest.remove(t.amount)
                    self._loo_cache[cache_key] = _stats(rest)
                return self._loo_cache[cache_key], level
        return None, ""

    def _feature_matrix(self, txns: list[Txn]) -> np.ndarray:
        rows = []
        for t in txns:
            la = math.log(t.amount)
            peer, _ = self._peer(t)
            h = t.occurred_at.hour + t.occurred_at.minute / 60
            rows.append([
                la,
                peer.z(la) if peer else 0.0,
                self.cat_counts.get(t.category, 0) / max(self.n, 1),
                math.sin(2 * math.pi * h / 24),
                math.cos(2 * math.pi * h / 24),
                1.0 if t.occurred_at.weekday() in (4, 5) else 0.0,
                t.n_participants / self.n_members,
            ])
        return np.array(rows)

    def isolation_ranks(self, txns: list[Txn]) -> list[float | None]:
        if self.forest is None or self.forest_train_scores is None:
            return [None] * len(txns)
        scores = -self.forest.score_samples(self._feature_matrix(txns))
        n = len(self.forest_train_scores)
        return [float(np.searchsorted(self.forest_train_scores, s, side="left") / n) for s in scores]

    # ------------------------------------------------------------------ scoring
    def score(self, t: Txn, isolation_rank: float | None = None, compute_isolation: bool = True) -> dict:
        in_hist = t.id in self.ids
        n_hist = self.n - (1 if in_hist else 0)
        signals: dict[str, float] = {}
        reasons: list[dict] = []
        la = math.log(t.amount)

        # 1) amount vs peers (same subcategory, else category)
        peer, level = self._peer(t, leave_one_out=in_hist)
        peer_z: float | None = None
        if peer is not None:
            z = peer_z = peer.z(la)
            signals["amount_peer"] = _clip01((z - 2.5) / 3.0)
            ratio = t.amount / peer.p90 if peer.p90 else 0.0
            if signals["amount_peer"] > 0 and ratio > 1:
                what = get_subcategory(t.subcategory).label if level == "subcategory" else t.category
                reasons.append({
                    "signal": "amount_peer", "strength": round(signals["amount_peer"], 2),
                    "text": f"{ratio:.1f}× the usual upper range for {what} in this group "
                            f"({fmt_taka(peer.p10)}–{fmt_taka(peer.p90)} across {peer.n} expenses)",
                    "evidence": {"ratio": round(ratio, 1), "typical_low": round(peer.p10 / 100),
                                 "typical_high": round(peer.p90 / 100), "peer_level": level, "peer_count": peer.n,
                                 "robust_z": round(z, 1)},
                })

        # 2) amount vs whole group
        if self.group_stats is not None and n_hist >= 10:
            z = self.group_stats.z(la)
            signals["amount_group"] = _clip01((z - 2.5) / 3.0)
            if peer_z is not None and peer_z < 2.0:
                # Large for the group but normal for its kind (e.g. monthly rent) → weak evidence.
                signals["amount_group"] *= 0.3
            below = bisect_left(self.sorted_amounts, t.amount)
            pct = 100.0 * below / max(n_hist, 1)
            if signals["amount_group"] > 0.3 and pct >= 97:
                text = (f"Largest of the group's {n_hist} recorded expenses" if pct >= 99.95 else
                        f"Larger than {math.floor(pct)}% of the group's {n_hist} recorded expenses")
                reasons.append({"signal": "amount_group", "strength": round(signals["amount_group"], 2), "text": text,
                                "evidence": {"percentile": round(min(pct, 100.0), 1), "history_count": n_hist}})

        # 3) isolation forest (multivariate context)
        if isolation_rank is None and compute_isolation:
            isolation_rank = self.isolation_ranks([t])[0]
        if isolation_rank is not None:
            signals["isolation"] = _clip01((isolation_rank - 0.95) / 0.05)
            if signals["isolation"] > 0.3:
                top = max(1, round((1 - isolation_rank) * 100))
                reasons.append({"signal": "isolation", "strength": round(signals["isolation"], 2),
                                "text": f"Isolation Forest ranks it in the top {top}% most unusual transactions for this "
                                        f"group (amount, timing, category and party size combined)",
                                "evidence": {"isolation_rank": round(isolation_rank, 3)}})

        # 4) night-time expense in a group that rarely spends at night
        if n_hist >= 20 and t.occurred_at.hour < 6:
            night = self.night_count - (1 if in_hist else 0)
            share = night / n_hist
            signals["time"] = 1.0 if share < 0.03 else _clip01((0.08 - share) / 0.05)
            if signals["time"] > 0:
                when = t.occurred_at.strftime("%I:%M %p").lstrip("0")
                text = (f"Recorded at {when} — no other expense in this group was recorded between midnight and 6 AM"
                        if night == 0 else
                        f"Recorded at {when} — only {share * 100:.1f}% of this group's expenses happen between "
                        f"midnight and 6 AM")
                reasons.append({"signal": "time", "strength": round(signals["time"], 2), "text": text,
                                "evidence": {"hour": t.occurred_at.hour, "night_share_pct": round(share * 100, 1)}})

        # 5) large expense in a category the group almost never uses
        if n_hist >= 30 and self.group_stats is not None:
            count = self.cat_counts.get(t.category, 0) - (1 if in_hist else 0)
            if count / n_hist < 0.02 and t.amount > 3 * math.exp(self.group_stats.med):
                signals["rare_category"] = 1.0
                reasons.append({"signal": "rare_category", "strength": 1.0,
                                "text": f"{t.category} is rare for this group ({count} other expense"
                                        f"{'' if count == 1 else 's'} out of {n_hist})",
                                "evidence": {"category_count": count, "history_count": n_hist}})

        # 6) possible duplicate (only the later entry of a pair is flagged)
        dup = self._find_duplicate(t)
        if dup is not None:
            signals["duplicate"] = 1.0
            minutes = abs((t.occurred_at - dup.occurred_at).total_seconds()) / 60
            reasons.append({"signal": "duplicate", "strength": 1.0,
                            "text": f"Possible duplicate: same amount ({fmt_taka(dup.amount)}) and description as an "
                                    f"expense recorded {minutes:.0f} min earlier",
                            "evidence": {"duplicate_of": dup.id, "minutes_apart": round(minutes)}})

        prod = 1.0
        for k, v in signals.items():
            prod *= 1 - WEIGHTS[k] * v
        score = 1 - prod
        reasons.sort(key=lambda r: WEIGHTS[r["signal"]] * r["strength"], reverse=True)
        return {
            "score": round(score, 3),
            "flagged": score >= FLAG_THRESHOLD,
            "signals": {k: round(v, 3) for k, v in signals.items()},
            "reasons": reasons,
            "history_count": n_hist,
            "limited_history": n_hist < MIN_HISTORY_FOR_FOREST,
            "model": {"name": MODEL_NAME, "version": MODEL_VERSION, "threshold": FLAG_THRESHOLD},
        }

    def _find_duplicate(self, t: Txn) -> Txn | None:
        for h in self.by_amount.get(t.amount, []):
            if h.id == t.id or abs((h.occurred_at - t.occurred_at).total_seconds()) > 30 * 60:
                continue
            same_merchant = bool(t.merchant and h.merchant and t.merchant.lower() == h.merchant.lower())
            same_desc = t.description.strip().lower() == h.description.strip().lower()
            if (same_merchant or same_desc) and (h.occurred_at, h.id) < (t.occurred_at, t.id):
                return h
        return None


def score_all(history: list[Txn], n_members: int) -> dict[str, dict]:
    """Batch-score a group's full history (used when seeding and for offline evaluation)."""
    model = GroupAnomalyModel(history, n_members)
    ranks = model.isolation_ranks(history)
    return {t.id: model.score(t, isolation_rank=r, compute_isolation=False) for t, r in zip(history, ranks)}
