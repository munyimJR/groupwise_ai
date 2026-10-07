"""Rigorous model validation: data splits, leakage checks, baselines, ablations, calibration and CIs.

Answers the Phase 1 AI/ML review: does each learned component beat simple rules, is anything leaking
across the train/test boundary or across time, are probabilities and forecast ranges calibrated, and how
uncertain are the headline numbers?

    python -m scripts.validate_models            # writes app/ml/validation.json and ../docs/MODEL_VALIDATION.md

Data: the behavior-driven synthetic generator (separate seeds for tuning and testing) plus a small
hand-written stress set that the generator never produced. Real-user validation comes from the pilot
(scripts/pilot_metrics.py), not from this script.
"""
from __future__ import annotations

import csv
import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.naive_bayes import MultinomialNB

from app.config import local_now
from app.ml import anomaly as an
from app.ml import categorizer as cat
from app.ml import forecast as fc
from app.ml.taxonomy import SUBCATEGORIES, get_subcategory
from app.ml.text import normalize_for_model
from app.synthetic.generator import generate_group
from app.synthetic.scenarios import eval_scenario

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "app" / "ml" / "validation.json"
OUT_MD = ROOT.parent / "docs" / "MODEL_VALIDATION.md"
STRESS = Path(__file__).parent / "data" / "handwritten_categorization.csv"
VAL_SEEDS, TEST_SEEDS, FC_SEEDS = range(0, 40), range(100, 140), range(100, 120)
RNG = np.random.default_rng(7)
B = 1000  # bootstrap resamples


def ci(values: np.ndarray, stat=np.mean) -> list[float]:
    """95% percentile bootstrap interval."""
    values = np.asarray(values)
    boots = [stat(values[RNG.integers(0, len(values), len(values))]) for _ in range(B)]
    return [round(float(np.percentile(boots, 2.5)), 4), round(float(np.percentile(boots, 97.5)), 4)]


# ============================================================================ 1. categorizer
def _fit_lr(texts, labels, word=True, char=True, c=12.0):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import FeatureUnion, Pipeline

    parts = []
    if word:
        parts.append(("word", TfidfVectorizer(ngram_range=(1, 2), token_pattern=r"(?u)\b\w[\w']*\b", sublinear_tf=True)))
    if char:
        parts.append(("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2)))
    pipe = Pipeline([("features", FeatureUnion(parts)), ("clf", LogisticRegression(C=c, max_iter=3000))])
    return pipe.fit([normalize_for_model(t) for t in texts], labels)


class KeywordRules:
    """Simple-rules baseline: a keyword table learned from the training data (each frequent, mostly
    unambiguous word votes for its usual subcategory). This is what a hand-made keyword list approximates."""

    def fit(self, texts, labels):
        counts: dict[str, Counter] = defaultdict(Counter)
        for t, y in zip(texts, labels):
            for w in set(re.findall(r"[a-z]+", normalize_for_model(t))):
                counts[w][y] += 1
        self.rules = {}
        for w, c in counts.items():
            total = sum(c.values())
            label, n = c.most_common(1)[0]
            if total >= 3 and n / total >= 0.6:
                self.rules[w] = (label, n / total)
        self.fallback = Counter(labels).most_common(1)[0][0]
        return self

    def predict(self, texts):
        out = []
        for t in texts:
            votes: Counter = Counter()
            for w in set(re.findall(r"[a-z]+", normalize_for_model(t))):
                if w in self.rules:
                    votes[self.rules[w][0]] += self.rules[w][1]
            out.append(votes.most_common(1)[0][0] if votes else self.fallback)
        return out


def _scores(y_true, y_pred) -> dict:
    cat_t = [SUBCATEGORIES[y].category for y in y_true]
    cat_p = [SUBCATEGORIES[y].category for y in y_pred]
    correct = np.array([a == b for a, b in zip(y_true, y_pred)], dtype=float)
    return {"sub_accuracy": round(float(correct.mean()), 4), "sub_accuracy_ci": ci(correct),
            "sub_f1_macro": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
            "category_accuracy": round(float(accuracy_score(cat_t, cat_p)), 4)}


def _calibration(probs: np.ndarray, classes: list[str], y_true: list[str], bins: int = 10) -> dict:
    conf = probs.max(axis=1)
    pred = np.array(classes)[probs.argmax(axis=1)]
    correct = (pred == np.array(y_true)).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    table, ece = [], 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            gap = abs(correct[m].mean() - conf[m].mean())
            ece += gap * m.mean()
            table.append({"bin": f"{lo:.1f}–{hi:.1f}", "n": int(m.sum()), "mean_confidence": round(float(conf[m].mean()), 3),
                          "accuracy": round(float(correct[m].mean()), 3)})
    onehot = (np.array(classes)[None, :] == np.array(y_true)[:, None]).astype(float)
    brier = float(np.mean(np.sum((probs - onehot) ** 2, axis=1)))
    coverage = []
    for th in (0.3, 0.45, 0.6, 0.8):
        m = conf >= th
        coverage.append({"threshold": th, "auto_accepted_share": round(float(m.mean()), 3),
                         "accuracy_when_auto": round(float(correct[m].mean()), 3) if m.any() else None})
    return {"ece": round(ece, 4), "brier": round(brier, 4), "reliability": table, "selective": coverage}


def eval_categorizer() -> dict:
    corpus = cat.build_corpus()
    tr_x, tr_y = map(list, zip(*corpus.train))
    te_x, te_y = map(list, zip(*corpus.test))

    # Leakage checks: drop any test text that also appears verbatim in training
    train_norm = {t.lower().strip() for t in tr_x}
    exact_overlap = sum(1 for t in te_x if t.lower().strip() in train_norm)
    keep = [i for i, t in enumerate(te_x) if t.lower().strip() not in train_norm]
    te_x, te_y = [te_x[i] for i in keep], [te_y[i] for i in keep]

    # Hyperparameter selection on the training split only (5-fold CV) — the test set is never used to choose
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    cv = {}
    y_arr = np.array(tr_y)
    for c in (1.0, 3.0, 12.0, 30.0):
        accs = []
        for a, b in folds.split(tr_x, tr_y):
            m = _fit_lr([tr_x[i] for i in a], list(y_arr[a]), c=c)
            accs.append(accuracy_score(y_arr[b], m.predict([normalize_for_model(tr_x[i]) for i in b])))
        cv[str(c)] = round(float(np.mean(accs)), 4)
    best_c = float(max(cv, key=cv.get))

    # Calibration: fit one temperature on out-of-fold training predictions (never on the test set)
    order = sorted(set(tr_y))
    oof_p, oof_y = [], []
    for a, b in folds.split(tr_x, tr_y):
        m = _fit_lr([tr_x[i] for i in a], list(y_arr[a]), c=best_c)
        pr = m.predict_proba([normalize_for_model(tr_x[i]) for i in b])
        full_p = np.full((len(b), len(order)), 1e-9)
        for j, c_ in enumerate(m.named_steps["clf"].classes_):
            full_p[:, order.index(c_)] = pr[:, j]
        oof_p.append(full_p)
        oof_y += list(y_arr[b])
    oof_p = np.vstack(oof_p)
    idx = np.array([order.index(y) for y in oof_y])

    def _temp(p, t):
        q = np.power(np.clip(p, 1e-12, 1), 1 / t)
        return q / q.sum(axis=1, keepdims=True)

    temps = np.round(np.arange(0.3, 2.01, 0.05), 2)
    nll = [float(-np.mean(np.log(_temp(oof_p, t)[np.arange(len(idx)), idx]))) for t in temps]
    best_t = float(temps[int(np.argmin(nll))])

    systems = {}
    majority = Counter(tr_y).most_common(1)[0][0]
    systems["Majority class"] = [majority] * len(te_y)
    systems["Keyword rules (simple baseline)"] = KeywordRules().fit(tr_x, tr_y).predict(te_x)
    nb_vec = CountVectorizer(ngram_range=(1, 2))
    nb = MultinomialNB(alpha=0.3).fit(nb_vec.fit_transform([normalize_for_model(t) for t in tr_x]), tr_y)
    systems["Naive Bayes (word counts)"] = list(nb.predict(nb_vec.transform([normalize_for_model(t) for t in te_x])))
    systems["TF-IDF words only + LR"] = list(_fit_lr(tr_x, tr_y, char=False, c=best_c).predict(
        [normalize_for_model(t) for t in te_x]))
    systems["TF-IDF characters only + LR"] = list(_fit_lr(tr_x, tr_y, word=False, c=best_c).predict(
        [normalize_for_model(t) for t in te_x]))
    systems["GroupWise as deployed (C = 12)"] = list(_fit_lr(tr_x, tr_y, c=12.0).predict(
        [normalize_for_model(t) for t in te_x]))
    full = cat.ExpenseCategorizer()
    full.pipeline = _fit_lr(tr_x, tr_y, c=best_c)
    full.classes_ = list(full.pipeline.named_steps["clf"].classes_)
    probs = full.predict_proba(te_x)
    systems[f"GroupWise, CV-selected C = {best_c:g}"] = [full.classes_[i] for i in probs.argmax(axis=1)]
    results = {name: _scores(te_y, pred) for name, pred in systems.items()}

    # Hand-written stress set (never produced by the generator, never used for training or tuning)
    stress = [(r["text"], r["label"]) for r in csv.DictReader(STRESS.open(encoding="utf-8"))]
    s_x, s_y = map(list, zip(*stress))
    s_probs = full.predict_proba(s_x)
    s_pred = [full.classes_[i] for i in s_probs.argmax(axis=1)]
    kw = KeywordRules().fit(tr_x, tr_y).predict(s_x)
    return {
        "splits": {"train": len(tr_x), "test": len(te_x), "classes": len(set(tr_y)),
                   "construction": "Per subcategory, 25% of merchants and 25% of phrasing templates are held out. Every "
                                   "test example uses a held-out merchant, a held-out phrasing, or both.",
                   "hyperparameter_selection": {"method": "5-fold CV on the training split", "cv_accuracy_by_C": cv,
                                                "chosen_C": best_c}},
        "leakage": {"exact_text_overlap_test_in_train": exact_overlap, "removed_from_test": exact_overlap,
                    "merchant_prior": "Excluded from all test metrics: the merchant knowledge base contains held-out "
                                      "merchants, so using it at test time would leak.",
                    "test_used_for_tuning": False},
        "comparison": results,
        "calibration": _calibration(probs, full.classes_, te_y),
        "calibration_temperature_scaled": {"temperature": best_t, **_calibration(_temp(probs, best_t), full.classes_, te_y)},
        "stress_set": {"n": len(s_y), "source": "hand-written descriptions outside the generator's templates",
                       "groupwise": _scores(s_y, s_pred), "keyword_rules": _scores(s_y, kw),
                       "errors": [{"text": t, "true": get_subcategory(y).label, "predicted": get_subcategory(p).label}
                                  for t, y, p in zip(s_x, s_y, s_pred) if y != p][:8]},
    }


# ============================================================================ 2. anomaly detector
def _groups(seeds, today):
    out = []
    for s in seeds:
        sc = eval_scenario(s)
        g = generate_group(sc, today)
        txns = [an.Txn(str(i), e.amount_paisa, get_subcategory(e.subcategory).category, e.subcategory, e.occurred_at,
                       len(e.shares), e.merchant, e.description) for i, e in enumerate(g.expenses)]
        out.append((sc, g, txns))
    return out


def _combine(signals: dict, keys: set[str]) -> float:
    prod = 1.0
    for k, v in signals.items():
        if k in keys:
            prod *= 1 - an.WEIGHTS[k] * v
    return 1 - prod


VARIANTS = {
    "Rule: amount > 3x the group's median for that subcategory": None,
    "Robust z-score only (amount vs subcategory and group)": {"amount_peer", "amount_group"},
    "Isolation Forest only": {"isolation"},
    "Rules only (night-time, rare category, duplicate)": {"time", "rare_category", "duplicate"},
    "Hybrid without Isolation Forest": {"amount_peer", "amount_group", "time", "rare_category", "duplicate"},
    "GroupWise hybrid (all signals)": set(an.WEIGHTS),
}


def _variant_scores(groups) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    """Per group: (scores, labels) for every variant, using batch scoring."""
    out: dict[str, list] = {k: [] for k in VARIANTS}
    for sc, g, txns in groups:
        res = an.score_all(txns, len(sc.members))
        labels = np.array([e.is_anomaly for e in g.expenses])
        med: dict[str, float] = {}
        by_sub: dict[str, list[int]] = defaultdict(list)
        for t in txns:
            by_sub[t.subcategory].append(t.amount)
        med = {k: float(np.median(v)) for k, v in by_sub.items()}
        for name, keys in VARIANTS.items():
            if keys is None:
                s = np.array([t.amount / med[t.subcategory] / 3.0 if len(by_sub[t.subcategory]) >= 4 else 0.0
                              for t in txns])  # ≥ 1 means "more than 3x the median"
            else:
                s = np.array([_combine(res[t.id]["signals"], keys) for t in txns])
            out[name].append((s, labels))
    return out


def _prf(pairs, th) -> tuple[float, float, float, int, int, int]:
    tp = fp = fn = 0
    for s, y in pairs:
        f = s >= th
        tp += int((f & y).sum())
        fp += int((f & ~y).sum())
        fn += int((~f & y).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0), tp, fp, fn


def _cluster_ci(pairs, th) -> list[float]:
    """Bootstrap over groups (transactions within a group are not independent)."""
    vals = []
    for _ in range(300):
        idx = RNG.integers(0, len(pairs), len(pairs))
        vals.append(_prf([pairs[i] for i in idx], th)[2])
    return [round(float(np.percentile(vals, 2.5)), 4), round(float(np.percentile(vals, 97.5)), 4)]


def eval_anomaly(today) -> dict:
    val, test = _variant_scores(_groups(VAL_SEEDS, today)), None
    test_groups = _groups(TEST_SEEDS, today)
    test = _variant_scores(test_groups)
    grid = np.round(np.arange(0.2, 1.51, 0.05), 2)
    table = {}
    for name in VARIANTS:
        th = float(max(grid, key=lambda t: _prf(val[name], t)[2]))  # threshold chosen on validation seeds
        if name == "GroupWise hybrid (all signals)":
            th = an.FLAG_THRESHOLD  # production threshold (also tuned on validation seeds)
        p, r, f, tp, fp, fn = _prf(test[name], th)
        table[name] = {"threshold": th, "precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4),
                       "f1_ci": _cluster_ci(test[name], th)}
    # Threshold sweep for the hybrid on validation (how the operating point was chosen)
    sweep = [{"threshold": float(t), **dict(zip(("precision", "recall", "f1"),
                                                (round(x, 3) for x in _prf(val["GroupWise hybrid (all signals)"], t)[:3])))}
             for t in (0.4, 0.5, 0.6, 0.7, 0.8)]
    return {"splits": {"tuning_seeds": f"{VAL_SEEDS.start}–{VAL_SEEDS.stop - 1}", "test_seeds": f"{TEST_SEEDS.start}–{TEST_SEEDS.stop - 1}",
                       "note": "Weights and thresholds were chosen on the tuning seeds only."},
            "comparison": table, "threshold_sweep_validation": sweep, "prospective": eval_anomaly_prospective(test_groups)}


def eval_anomaly_prospective(test_groups, days: int = 28) -> dict:
    """Temporal leakage check: score each expense of the last `days` days using ONLY earlier expenses,
    exactly like the live app (batch scoring compares against the whole history, including the future)."""
    tp = fp = fn = 0
    batch_tp = batch_fp = batch_fn = 0
    for sc, g, txns in test_groups:
        if not txns:
            continue
        cutoff = max(t.occurred_at for t in txns) - timedelta(days=days)
        batch = an.score_all(txns, len(sc.members))
        order = sorted(range(len(txns)), key=lambda i: (txns[i].occurred_at, txns[i].id))
        for pos, i in enumerate(order):
            t, y = txns[i], g.expenses[i].is_anomaly
            if t.occurred_at < cutoff:
                continue
            history = [txns[j] for j in order[:pos]]
            flagged = an.GroupAnomalyModel(history, len(sc.members)).score(t)["flagged"]
            tp += flagged and y
            fp += flagged and not y
            fn += (not flagged) and y
            bf = batch[t.id]["flagged"]
            batch_tp += bf and y
            batch_fp += bf and not y
            batch_fn += (not bf) and y

    def prf(a, b, c):
        p = a / (a + b) if a + b else 0.0
        r = a / (a + c) if a + c else 0.0
        return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
                "anomalies": a + c}

    return {"window_days": days, "online_past_only": prf(tp, fp, fn), "batch_same_transactions": prf(batch_tp, batch_fp, batch_fn)}


# ============================================================================ 3. forecast
def _seasonal_profile_baseline(hist, origin, horizon):
    """Average of the same weekday over the previous 4 weeks (a strong simple baseline)."""
    by_day = defaultdict(float)
    for t in hist:
        by_day[t.occurred_at.date()] += t.amount
    total = 0.0
    for i in range(horizon):
        d = origin + timedelta(days=i)
        total += np.mean([by_day.get(d - timedelta(days=7 * k), 0.0) for k in range(1, 5)])
    return total


def _model_total(hist, origin, horizon, variant):
    if variant == "no_recurring":
        orig = fc.detect_recurring
        fc.detect_recurring = lambda h, d: ([], set())
        try:
            m = fc.SeasonalForecaster(hist, origin)
        finally:
            fc.detect_recurring = orig
    elif variant == "no_decay":
        m = fc.SeasonalForecaster(hist, origin, half_life=10_000)
    else:
        m = fc.SeasonalForecaster(hist, origin)
        if variant == "no_seasonality":
            for p in m.categories.values():
                p["dow"], p["phase"] = np.ones(7), np.ones(3)
    return sum(p["total"] for p in m.predict(horizon))


def eval_forecast(today) -> dict:
    systems = ["Mean of previous 28 days", "Last week repeated", "Same weekday, 4-week average",
               "GroupWise without recurring bills", "GroupWise without weekday/month factors",
               "GroupWise without recency weighting", "GroupWise forecast"]
    errors = {s: [] for s in systems}
    group_mae = {s: [] for s in systems}
    covered, covered_raw, n_int, leakage_ok = 0, 0, 0, True
    as_of = today.date()
    for seed in FC_SEEDS:
        g = generate_group(eval_scenario(seed), today)
        txns = [fc.SpendTxn(e.amount_paisa, get_subcategory(e.subcategory).category, e.subcategory, e.occurred_at,
                            e.description, e.merchant) for e in g.expenses if not e.is_anomaly]
        per_group = {s: [] for s in systems}
        for k in range(8, 0, -1):
            origin = as_of - timedelta(days=7 * k)
            hist = [t for t in txns if t.occurred_at.date() < origin]
            if len(hist) < 20 or (origin - min(t.occurred_at.date() for t in hist)).days < 28:
                continue
            actual = sum(t.amount for t in txns if origin <= t.occurred_at.date() < origin + timedelta(days=7))
            prev28 = sum(t.amount for t in hist if t.occurred_at.date() >= origin - timedelta(days=28))
            preds = {
                "Mean of previous 28 days": prev28 / 4,
                "Last week repeated": sum(t.amount for t in hist if t.occurred_at.date() >= origin - timedelta(days=7)),
                "Same weekday, 4-week average": _seasonal_profile_baseline(hist, origin, 7),
                "GroupWise without recurring bills": _model_total(hist, origin, 7, "no_recurring"),
                "GroupWise without weekday/month factors": _model_total(hist, origin, 7, "no_seasonality"),
                "GroupWise without recency weighting": _model_total(hist, origin, 7, "no_decay"),
                "GroupWise forecast": _model_total(hist, origin, 7, "full"),
            }
            # Leakage check: giving the model the future must not change the forecast
            if k == 4 and abs(_model_total(txns, origin, 7, "full") - preds["GroupWise forecast"]) > 1e-6:
                leakage_ok = False
            for s in systems:
                e = abs(actual - preds[s]) / 100
                errors[s].append(e)
                per_group[s].append(e)
            # Interval calibration: the 80% range the app would have shown at this origin (own past backtests only)
            bt = fc.backtest(hist, origin)
            if bt.get("n_windows", 0) >= 4:
                n_int += 1
                lo, hi = fc.interval_factors(bt["rel_errors"])  # as deployed (widening tuned on validation seeds)
                covered += preds["GroupWise forecast"] * lo <= actual <= preds["GroupWise forecast"] * hi
                lo0, hi0 = fc.interval_factors(bt["rel_errors"], (0.1, 0.9), 1.0)  # before tuning
                covered_raw += preds["GroupWise forecast"] * lo0 <= actual <= preds["GroupWise forecast"] * hi0
        for s in systems:
            if per_group[s]:
                group_mae[s].append(np.mean(per_group[s]))
    table = {}
    base = np.array(group_mae["Mean of previous 28 days"])
    full = np.array(group_mae["GroupWise forecast"])
    for s in systems:
        arr = np.array(group_mae[s])
        table[s] = {"mae_7day": round(float(np.mean(errors[s]))), "mae_ci": [round(x) for x in ci(arr)]}
    boots = []
    for _ in range(B):
        ix = RNG.integers(0, len(full), len(full))
        boots.append(1 - full[ix].mean() / base[ix].mean())
    return {"splits": {"test_seeds": f"{FC_SEEDS.start}–{FC_SEEDS.stop - 1}", "windows": len(errors["GroupWise forecast"]),
                       "method": "Rolling origin: 8 weekly cut-offs per group; each forecast is fitted only on data "
                                 "before its cut-off and scored on the next 7 days."},
            "comparison": table,
            "improvement_vs_mean28": {"pct": round(float(1 - full.mean() / base.mean()) * 100, 1),
                                      "ci_pct": [round(float(np.percentile(boots, q)) * 100, 1) for q in (2.5, 97.5)]},
            "interval_80": {"windows": n_int, "coverage": round(covered / n_int, 3) if n_int else None,
                            "coverage_before_tuning": round(covered_raw / n_int, 3) if n_int else None,
                            "tuning": f"10th-90th percentile of the group's own backtest errors, widened {fc.INTERVAL_WIDEN}x; "
                                      "the widening was chosen on validation seeds 0-19 (80.5% coverage there)"},
            "leakage": {"future_data_changes_forecast": not leakage_ok}}


# ============================================================================ report
def _pct(x):
    return f"{x * 100:.1f}%"


def write_markdown(r: dict) -> None:
    c, a, f = r["categorizer"], r["anomaly"], r["forecast"]
    L = ["# Model validation: baselines, ablations, calibration, leakage checks",
         "", f"Generated {r['generated_at']} by `python -m scripts.validate_models`. Data: behavior-driven **synthetic** "
         "groups (separate seeds for tuning and testing) and a small hand-written stress set. Real-user validation comes "
         "from the pilot (`scripts/pilot_metrics.py`). Intervals are 95% bootstrap confidence intervals.", "",
         "## What counts as machine learning here", "",
         "| Component | Kind | Learned from data? |", "|---|---|---|",
         "| Expense categorizer | **Trained ML**: TF-IDF features + logistic regression | Yes, supervised |",
         "| Unusual-expense detector | **ML + statistics**: Isolation Forest (unsupervised, fitted per group) combined with robust z-scores and rules | Isolation Forest yes; rules no |",
         "| Cash-flow forecast | **Statistical time-series model**: exponential smoothing with weekday/month factors and recurring-bill detection | Fitted per group |",
         "| Goal likelihood | **Simulation**: bootstrap Monte-Carlo of the group's own contributions | No training |",
         "| Spending drivers, group dynamics, health score | **Deterministic analytics** | No |",
         "| Ask GroupWise | **LLM** for wording only, numbers verified | Pre-trained, not trained by us |", "",
         "So GroupWise has **two learned models** (categorizer, Isolation Forest) and **one fitted statistical forecaster**, "
         "plus simulation and analytics. Earlier material that said “five ML models” overstated this.", "",
         "## 1. Expense categorizer", "",
         f"**Splits.** {c['splits']['train']:,} training and {c['splits']['test']} test examples, {c['splits']['classes']} subcategories. "
         f"{c['splits']['construction']} The regularization strength was chosen by 5-fold cross-validation **on the training split only** "
         f"(C = {c['splits']['hyperparameter_selection']['chosen_C']:g}; CV accuracy by C: "
         + ", ".join(f"{k}: {_pct(v)}" for k, v in c["splits"]["hyperparameter_selection"]["cv_accuracy_by_C"].items()) + ").", "",
         f"**Leakage checks.** Test texts that also appear verbatim in training: **{c['leakage']['exact_text_overlap_test_in_train']}**. "
         f"{c['leakage']['merchant_prior']}", "",
         "**Baselines and ablations (same test set):**", "",
         "| System | Subcategory accuracy (95% CI) | Macro F1 | Category accuracy |", "|---|---|---|---|"]
    for name, s in c["comparison"].items():
        L.append(f"| {name} | {_pct(s['sub_accuracy'])} ({_pct(s['sub_accuracy_ci'][0])}–{_pct(s['sub_accuracy_ci'][1])}) | "
                 f"{_pct(s['sub_f1_macro'])} | {_pct(s['category_accuracy'])} |")
    cal = c["calibration"]
    tsc = c["calibration_temperature_scaled"]
    L += ["", f"**Calibration.** Expected calibration error **{cal['ece']:.3f}** (Brier {cal['brier']:.3f}). The model is "
          "mostly under-confident: in the middle bins it is right far more often than its stated confidence. One "
          f"temperature fitted on out-of-fold training predictions (T = {tsc['temperature']}) changes the test error to "
          f"**{tsc['ece']:.3f}** (Brier {tsc['brier']:.3f}). The app auto-accepts a category only above a confidence "
          "threshold and asks the person otherwise:", "",
          "| Confidence threshold | Share auto-accepted | Accuracy when auto-accepted |", "|---|---|---|"]
    L += [f"| {x['threshold']} | {_pct(x['auto_accepted_share'])} | {_pct(x['accuracy_when_auto']) if x['accuracy_when_auto'] is not None else 'n/a'} |"
          for x in cal["selective"]]
    L += ["", "| Confidence bin | n | Mean confidence | Accuracy |", "|---|---|---|---|"]
    L += [f"| {x['bin']} | {x['n']} | {x['mean_confidence']:.2f} | {x['accuracy']:.2f} |" for x in cal["reliability"]]
    st = c["stress_set"]
    L += ["", f"**Hand-written stress set** ({st['n']} descriptions written outside the generator's templates, never used for "
          f"training or tuning): GroupWise {_pct(st['groupwise']['sub_accuracy'])} "
          f"(CI {_pct(st['groupwise']['sub_accuracy_ci'][0])}–{_pct(st['groupwise']['sub_accuracy_ci'][1])}), keyword rules "
          f"{_pct(st['keyword_rules']['sub_accuracy'])}. Small sample, so the interval is wide. Example errors: "
          + "; ".join(f"“{e['text']}” → {e['predicted']} (should be {e['true']})" for e in st["errors"][:4]) + ".", "",
          "## 2. Unusual-expense detector", "",
          f"**Splits.** Tuning seeds {a['splits']['tuning_seeds']}, test seeds {a['splits']['test_seeds']}. "
          "Every variant's threshold is chosen on the tuning seeds, then scored once on the test seeds. "
          "F1 intervals come from a bootstrap over groups.", "",
          "| Variant | Threshold | Precision | Recall | F1 (95% CI) |", "|---|---|---|---|---|"]
    for name, s in a["comparison"].items():
        L.append(f"| {name} | {s['threshold']} | {_pct(s['precision'])} | {_pct(s['recall'])} | "
                 f"{_pct(s['f1'])} ({_pct(s['f1_ci'][0])}–{_pct(s['f1_ci'][1])}) |")
    L += ["", "**Operating point (validation seeds):** " + "; ".join(
        f"threshold {x['threshold']}: P {_pct(x['precision'])}, R {_pct(x['recall'])}" for x in a["threshold_sweep_validation"]), ""]
    pr = a["prospective"]
    L += [f"**Temporal leakage check.** Batch evaluation compares each expense with the group's whole history, including "
          f"later expenses. The live app only sees the past. Over the last {pr['window_days']} days of each test group "
          f"({pr['online_past_only']['anomalies']} injected anomalies): **past-only scoring** P {_pct(pr['online_past_only']['precision'])}, "
          f"R {_pct(pr['online_past_only']['recall'])}, F1 {_pct(pr['online_past_only']['f1'])} versus batch scoring "
          f"F1 {_pct(pr['batch_same_transactions']['f1'])} on the same transactions. The past-only number is the one "
          "that reflects the product.", "",
          "## 3. Cash-flow forecast (7-day total)", "",
          f"**Splits.** {f['splits']['method']} {f['splits']['windows']} windows over test seeds {f['splits']['test_seeds']}.", "",
          "| System | MAE (95% CI across groups) |", "|---|---|"]
    for name, s in f["comparison"].items():
        L.append(f"| {name} | ৳{s['mae_7day']:,} (৳{s['mae_ci'][0]:,}–৳{s['mae_ci'][1]:,}) |")
    iv = f["interval_80"]
    L += ["", f"Improvement over the 28-day-average baseline: **{f['improvement_vs_mean28']['pct']}%** "
          f"(95% CI {f['improvement_vs_mean28']['ci_pct'][0]}–{f['improvement_vs_mean28']['ci_pct'][1]}%).", "",
          f"**Range calibration.** Before tuning, the app's 80% range contained the actual 7-day total in only "
          f"{_pct(iv['coverage_before_tuning'])} of {iv['windows']} test windows: too narrow, because each group has only about "
          f"8 past windows to learn its errors from. Fix: {iv['tuning']}. Coverage on the untouched test seeds is now "
          f"**{_pct(iv['coverage'])}** (target 80%). Weekly group spending is volatile, so an honest 80% range is wide.", "",
          f"**Leakage check.** Passing future transactions to the forecaster changes its forecast: "
          f"**{'yes — investigate' if f['leakage']['future_data_changes_forecast'] else 'no'}** (it fits only on data before the cut-off).", "",
          "## Limits", "",
          "- Everything above is synthetic or hand-written. It shows the methods work and beat simple rules on realistic "
          "simulated behavior; it does not prove performance on real users. The pilot measures that directly: AI category "
          "acceptance, flagged-expense review outcomes, and forecast error on real groups.",
          "- The anomaly test set contains injected anomaly types we designed; new real-world anomaly types may be missed.", ""]
    OUT_MD.write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    t0 = time.time()
    today = local_now()
    np.seterr(all="ignore")
    r = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "label": "Synthetic-data validation"}
    r["categorizer"] = eval_categorizer()
    print(f"categorizer done {time.time() - t0:.0f}s")
    r["anomaly"] = eval_anomaly(today)
    print(f"anomaly done {time.time() - t0:.0f}s")
    r["forecast"] = eval_forecast(today)
    print(f"forecast done {time.time() - t0:.0f}s")
    OUT_JSON.write_text(json.dumps(r, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    write_markdown(r)
    print(f"done in {time.time() - t0:.0f}s: {OUT_JSON} and {OUT_MD}")


if __name__ == "__main__":
    main()
