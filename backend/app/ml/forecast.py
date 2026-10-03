"""AI Feature 4 — Group cash-flow forecast.

Forecast = detected recurring bills (scheduled on their expected dates)
         + variable spending, modelled per category with seasonal exponential smoothing:

    ŷ(day) = level_c × weekday_factor_c[dow] × month_phase_factor_c[phase]

  * level      — exponentially weighted mean of de-seasonalised daily spend (half-life 14 days),
                 so recent behaviour (e.g. rising weekend dining) carries more weight
  * weekday    — how much a given weekday differs from an average day, shrunk toward 1
                 when a category has little history (empirical-Bayes style shrinkage)
  * month phase — start-of-month (days 1–7) / mid / end (24+) effect, also shrunk

Uncertainty comes from the group's own rolling-origin backtest: the model is re-fitted at
several past cut-off dates, the next 7 days are predicted, and the empirical distribution of
relative errors gives the interval and a confidence label. Flagged, unreviewed anomalies are
excluded from training so one strange expense does not inflate the forecast.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np

MODEL_NAME = "cashflow-forecast"
MODEL_VERSION = "seasonal-ets-1.0"
HALF_LIFE_DAYS = 14
LOOKBACK_DAYS = 120
SHRINK_DOW = 6.0  # pseudo-observations pulling weekday factors toward 1
SHRINK_PHASE = 6.0
RECURRING_SUBS = {"rent", "electricity", "gas", "water", "internet", "home_services", "subscriptions", "mobile_recharge"}
DOW_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@dataclass
class SpendTxn:
    amount: int  # paisa
    category: str
    subcategory: str
    occurred_at: datetime
    description: str = ""
    merchant: str | None = None


@dataclass
class RecurringBill:
    key: str
    label: str
    subcategory: str
    category: str
    amount: int
    next_date: date
    occurrences: int
    interval_days: float


def _phase(d: date) -> int:
    return 0 if d.day <= 7 else (2 if d.day >= 24 else 1)


def _month_day(year: int, month: int, day: int) -> date:
    while month > 12:
        month -= 12
        year += 1
    for d in (day, 30, 29, 28):
        try:
            return date(year, month, d)
        except ValueError:
            continue
    return date(year, month, 28)


def detect_recurring(txns: list[SpendTxn], as_of: date) -> tuple[list[RecurringBill], set[int]]:
    """Find monthly bills: same subcategory (+ merchant), ≥2 roughly monthly payments with stable amounts.

    Monthly bills follow the calendar, so the next due date is the usual day-of-month in the
    following month (not "last date + average gap", which drifts). A bill whose usual date
    passed within the last week without a payment is treated as due now.
    """
    groups: dict[tuple[str, str], list[tuple[int, SpendTxn]]] = defaultdict(list)
    for i, t in enumerate(txns):
        if t.subcategory in RECURRING_SUBS:
            groups[(t.subcategory, (t.merchant or "").lower())].append((i, t))
    bills: list[RecurringBill] = []
    used: set[int] = set()
    for (sub, merchant), items in groups.items():
        if len(items) < 2:
            continue
        items.sort(key=lambda it: it[1].occurred_at)
        dates = [it[1].occurred_at.date() for it in items]
        gaps = np.diff([d.toordinal() for d in dates])
        amounts = np.array([it[1].amount for it in items], dtype=float)
        med_gap = float(np.median(gaps))
        cv = float(np.std(amounts) / np.mean(amounts)) if amounts.mean() else 1.0
        if not (24 <= med_gap <= 36) or cv > (0.35 if len(items) >= 3 else 0.15):
            continue
        dom = int(np.median([d.day for d in dates]))
        last = dates[-1]
        nxt = _month_day(last.year, last.month + 1, dom)
        if (nxt - last).days < 20:  # paid late last month → next is the month after
            nxt = _month_day(last.year, last.month + 2, dom)
        while (as_of - nxt).days > 7:  # long overdue → assume it moved to the next cycle
            nxt = _month_day(nxt.year, nxt.month + 1, dom)
        if nxt <= as_of:
            nxt = as_of + timedelta(days=1)  # due date just passed without a payment → due now
        t0 = items[-1][1]
        bills.append(RecurringBill(f"{sub}:{merchant}", t0.description, sub, t0.category, int(np.median(amounts)), nxt,
                                   len(items), med_gap))
        used.update(i for i, _ in items)
    return bills, used


class SeasonalForecaster:
    def __init__(self, txns: list[SpendTxn], as_of: date, half_life: float | None = None):
        """Fit on all transactions strictly before `as_of`."""
        self.as_of = as_of
        self.half_life = half_life or HALF_LIFE_DAYS
        history = [t for t in txns if t.occurred_at.date() < as_of]
        self.history = history
        self.recurring, used = detect_recurring(history, as_of - timedelta(days=1))
        variable = [t for i, t in enumerate(history) if i not in used]
        start = max(as_of - timedelta(days=LOOKBACK_DAYS), min((t.occurred_at.date() for t in history), default=as_of))
        self.start = start
        self.n_days = max((as_of - start).days, 0)
        self.categories: dict[str, dict] = {}
        series: dict[str, np.ndarray] = defaultdict(lambda: np.zeros(self.n_days))
        for t in variable:
            idx = (t.occurred_at.date() - start).days
            if 0 <= idx < self.n_days:
                series[t.category][idx] += t.amount
        days = [start + timedelta(days=i) for i in range(self.n_days)]
        dows = np.array([d.weekday() for d in days])
        phases = np.array([_phase(d) for d in days])
        for cat, y in series.items():
            if y.sum() <= 0:
                continue
            # Winsorise extreme days (p98) so one-off spikes don't dominate the level.
            cap = np.percentile(y[y > 0], 98) if (y > 0).sum() >= 10 else y.max()
            y = np.minimum(y, cap)
            mean = y.mean() or 1.0
            dow_f = np.ones(7)
            for d in range(7):
                mask = dows == d
                n = mask.sum()
                raw = (y[mask].mean() / mean) if n else 1.0
                weeks = n
                dow_f[d] = (raw * weeks + SHRINK_DOW) / (weeks + SHRINK_DOW)
            dow_f /= dow_f.mean()
            phase_f = np.ones(3)
            for p in range(3):
                mask = phases == p
                n_months = mask.sum() / 10.0
                raw = (y[mask].mean() / mean) if mask.any() else 1.0
                phase_f[p] = (raw * n_months + SHRINK_PHASE) / (n_months + SHRINK_PHASE)
            deseason = y / (dow_f[dows] * phase_f[phases])
            alpha = 1 - 0.5 ** (1 / self.half_life)
            weights = (1 - alpha) ** np.arange(self.n_days - 1, -1, -1)
            level = float((deseason * weights).sum() / weights.sum())
            recent = y[-28:].sum() if self.n_days >= 28 else y.sum()
            prior = y[-56:-28].sum() if self.n_days >= 56 else None
            self.categories[cat] = {"level": level, "dow": dow_f, "phase": phase_f, "recent_28": float(recent),
                                    "prior_28": float(prior) if prior is not None else None}

    def predict_day(self, d: date) -> dict[str, float]:
        out = {c: p["level"] * p["dow"][d.weekday()] * p["phase"][_phase(d)] for c, p in self.categories.items()}
        for bill in self.recurring:
            nxt = bill.next_date
            dom = nxt.day
            while nxt < d:
                nxt = _month_day(nxt.year, nxt.month + 1, dom)
            if nxt == d:
                out[bill.category] = out.get(bill.category, 0.0) + bill.amount
        return out

    def predict(self, horizon: int) -> list[dict]:
        rows = []
        for i in range(horizon):
            d = self.as_of + timedelta(days=i)
            by_cat = self.predict_day(d)
            rows.append({"date": d, "total": float(sum(by_cat.values())), "by_category": by_cat})
        return rows


def backtest(txns: list[SpendTxn], as_of: date, n_origins: int = 8, horizon: int = 7,
             half_life: float | None = None) -> dict:
    """Rolling-origin evaluation on the group's own history (weekly cut-offs).

    Reports error on the 7-day total (what the product shows) and on daily values, against two
    baselines: the mean of the previous 28 days, and last week's total ("seasonal naive").
    """
    rel_errors: list[float] = []
    tot_err, base_mean_err, base_naive_err = [], [], []
    abs_daily, base_abs_daily = [], []
    for k in range(n_origins, 0, -1):
        origin = as_of - timedelta(days=7 * k)
        hist = [t for t in txns if t.occurred_at.date() < origin]
        if len(hist) < 20 or (origin - min(t.occurred_at.date() for t in hist)).days < 28:
            continue
        model = SeasonalForecaster(hist, origin, half_life=half_life)
        preds = model.predict(horizon)
        actual_by_day: dict[date, float] = defaultdict(float)
        for t in txns:
            dd = t.occurred_at.date()
            if origin <= dd < origin + timedelta(days=horizon):
                actual_by_day[dd] += t.amount
        prev28 = sum(t.amount for t in hist if t.occurred_at.date() >= origin - timedelta(days=28))
        prev7 = sum(t.amount for t in hist if t.occurred_at.date() >= origin - timedelta(days=7))
        actual_total = sum(actual_by_day.values())
        pred_total = sum(p["total"] for p in preds)
        if pred_total > 0:
            rel_errors.append((actual_total - pred_total) / pred_total)
        tot_err.append(actual_total - pred_total)
        base_mean_err.append(actual_total - prev28 / 28.0 * horizon)
        base_naive_err.append(actual_total - prev7)
        for p in preds:
            a = actual_by_day.get(p["date"], 0.0)
            abs_daily.append(abs(a - p["total"]))
            base_abs_daily.append(abs(a - prev28 / 28.0))
    if not rel_errors:
        return {"n_windows": 0}

    def mae(e: list[float]) -> float:
        return float(np.mean(np.abs(e))) / 100

    def rmse(e: list[float]) -> float:
        return float(math.sqrt(np.mean(np.square(e)))) / 100

    return {
        "n_windows": len(rel_errors),
        "mae_7day": mae(tot_err), "rmse_7day": rmse(tot_err),
        "baseline_mean28_mae_7day": mae(base_mean_err), "baseline_mean28_rmse_7day": rmse(base_mean_err),
        "baseline_lastweek_mae_7day": mae(base_naive_err), "baseline_lastweek_rmse_7day": rmse(base_naive_err),
        "mae_daily": float(np.mean(abs_daily)) / 100, "baseline_mae_daily": float(np.mean(base_abs_daily)) / 100,
        "weekly_mape": float(np.mean(np.abs(rel_errors))),
        "bias_pct": float(np.mean(rel_errors)) * 100,
        "rel_error_q10": float(np.quantile(rel_errors, 0.1)),
        "rel_error_q90": float(np.quantile(rel_errors, 0.9)),
    }


def forecast_group(txns: list[SpendTxn], as_of: date, horizon: int = 7, with_backtest: bool = True) -> dict:
    """Full forecast payload (amounts in paisa) with interval, drivers and pressure days."""
    if not txns:
        return {"status": "insufficient_data", "message": "Add a few weeks of shared expenses to unlock forecasting."}
    first = min(t.occurred_at.date() for t in txns)
    history_days = (as_of - first).days
    if history_days < 21 or len(txns) < 15:
        return {"status": "insufficient_data", "history_days": history_days, "transactions": len(txns),
                "message": "More transaction history is needed to generate a reliable forecast (≈3 weeks)."}

    last_activity = max(t.occurred_at.date() for t in txns)
    if (as_of - last_activity).days > 21:
        return {"status": "inactive", "last_activity": last_activity.isoformat(),
                "message": "No shared spending in the last 3 weeks, so there is no recent pattern to project. "
                           "Forecasts resume once the group is active again."}

    model = SeasonalForecaster(txns, as_of)
    preds = model.predict(horizon)
    total = sum(p["total"] for p in preds)
    bt = backtest(txns, as_of) if with_backtest else {"n_windows": 0}

    if bt.get("n_windows", 0) >= 4:
        lo_f, hi_f = 1 + min(bt["rel_error_q10"], -0.08), 1 + max(bt["rel_error_q90"], 0.08)
        mape = bt["weekly_mape"]
        confidence = "high" if mape < 0.15 and history_days >= 60 else ("medium" if mape < 0.3 else "low")
    else:
        lo_f, hi_f, mape, confidence = 0.7, 1.3, None, "low"
    # Relative errors come from 7-day backtests and are applied as-is to other horizons (approximation).

    # Historical comparison: actual spend in the same-length window before as_of
    last_window = sum(t.amount for t in txns if as_of - timedelta(days=horizon) <= t.occurred_at.date() < as_of)
    hist_days = [t for t in txns if t.occurred_at.date() >= as_of - timedelta(days=56)]
    avg_daily_8w = sum(t.amount for t in hist_days) / 56.0

    by_cat: dict[str, float] = defaultdict(float)
    for p in preds:
        for c, v in p["by_category"].items():
            by_cat[c] += v
    avg_pred = total / horizon if horizon else 0
    pressure = [p for p in preds if p["total"] > 1.25 * avg_pred and p["total"] > 1.15 * avg_daily_8w]

    drivers: list[dict] = []
    # weekday seasonality driver
    combined_dow = np.zeros(7)
    for c, p in model.categories.items():
        combined_dow += p["level"] * p["dow"]
    if combined_dow.sum() > 0:
        rel = combined_dow / combined_dow.mean()
        top = np.argsort(rel)[::-1][:3]
        top_days = sorted(int(i) for i in top if rel[i] > 1.1)
        if top_days:
            drivers.append({"kind": "weekly_pattern",
                            "text": f"{', '.join(DOW_NAMES[i] for i in top_days)} are historically the group's "
                                    f"heaviest days ({rel[top[0]]:.1f}× an average day)",
                            "evidence": {"days": [DOW_NAMES[i] for i in top_days], "peak_multiplier": round(float(rel[top[0]]), 2)}})
    # trend driver
    for c, p in sorted(model.categories.items(), key=lambda kv: kv[1]["recent_28"], reverse=True)[:4]:
        if p["prior_28"] and p["prior_28"] > 0:
            chg = p["recent_28"] / p["prior_28"] - 1
            if abs(chg) >= 0.15 and p["recent_28"] >= 0.1 * sum(q["recent_28"] for q in model.categories.values()):
                drivers.append({"kind": "trend", "category": c,
                                "text": f"{c} spending is trending {'up' if chg > 0 else 'down'}: last 28 days "
                                        f"{'+' if chg > 0 else ''}{chg * 100:.0f}% vs the previous 28 days",
                                "evidence": {"category": c, "change_pct": round(chg * 100, 1),
                                             "recent_28": round(p["recent_28"] / 100), "prior_28": round(p["prior_28"] / 100)}})
    for bill in model.recurring:
        if bill.next_date < as_of + timedelta(days=horizon):
            drivers.append({"kind": "recurring", "category": bill.category,
                            "text": f"Recurring {bill.label} (~৳{bill.amount / 100:,.0f}) expected on "
                                    f"{bill.next_date.strftime('%b %d')} — detected from {bill.occurrences} previous payments",
                            "evidence": {"amount": round(bill.amount / 100), "date": bill.next_date.isoformat(),
                                         "occurrences": bill.occurrences}})

    change_vs_last = (total / last_window - 1) if last_window else None
    return {
        "status": "ok",
        "horizon_days": horizon,
        "as_of": as_of.isoformat(),
        "total": round(total),
        "interval": {"low": round(total * lo_f), "high": round(total * hi_f), "level": 0.8},
        "confidence": confidence,
        "daily": [{"date": p["date"].isoformat(), "dow": DOW_NAMES[p["date"].weekday()], "total": round(p["total"]),
                   "low": round(p["total"] * lo_f), "high": round(p["total"] * hi_f),
                   "by_category": {c: round(v) for c, v in p["by_category"].items() if v >= 50}} for p in preds],
        "by_category": [{"category": c, "total": round(v)} for c, v in sorted(by_cat.items(), key=lambda kv: -kv[1]) if v >= 100],
        "pressure_days": [{"date": p["date"].isoformat(), "dow": DOW_NAMES[p["date"].weekday()], "total": round(p["total"])}
                          for p in pressure],
        "recurring": [{"label": b.label, "category": b.category, "amount": b.amount, "next_date": b.next_date.isoformat(),
                       "occurrences": b.occurrences} for b in model.recurring],
        "comparison": {"last_period_actual": last_window, "avg_daily_8w": round(avg_daily_8w),
                       "change_vs_last_period_pct": round(change_vs_last * 100, 1) if change_vs_last is not None else None},
        "drivers": drivers,
        "history_days": history_days,
        "transactions_used": len(model.history),
        "backtest": bt,
        "model": {"name": MODEL_NAME, "version": MODEL_VERSION, "method": "Recurring-bill detection + per-category "
                  "seasonal exponential smoothing (weekday & month-phase factors)", "weekly_mape": mape},
    }
