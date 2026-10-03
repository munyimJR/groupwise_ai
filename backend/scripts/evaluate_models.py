"""Evaluate the ML components on synthetic data and write the results.

Outputs:
  app/ml/evaluation.json   — served by GET /api/meta/models (shown on the Responsible AI page)
  ../docs/MODEL_EVALUATION.md

Methodology (all labelled "synthetic-data simulation"):
  * Categorizer — trained on the training split; tested on held-out merchants AND held-out phrasings.
  * Anomaly detector — thresholds/weights were tuned on evaluation seeds 0–39 ("validation");
    reported metrics come from untouched seeds 100–139 ("test").
  * Forecast — rolling-origin backtests (8 weekly origins, 7-day horizon) on test seeds 100–119,
    compared with two naive baselines.

Usage:  python -m scripts.evaluate_models
"""
from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import local_now
from app.ml import anomaly as anomaly_mod
from app.ml import categorizer as cat_mod
from app.ml import forecast as fc_mod
from app.ml.anomaly import Txn, score_all
from app.ml.forecast import SpendTxn, backtest
from app.ml.taxonomy import get_subcategory
from app.synthetic.generator import generate_group
from app.synthetic.scenarios import eval_scenario

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "app" / "ml" / "evaluation.json"
OUT_MD = ROOT.parent / "docs" / "MODEL_EVALUATION.md"


def eval_categorizer() -> dict:
    corpus = cat_mod.build_corpus()
    texts, labels = zip(*corpus.train)
    model = cat_mod.ExpenseCategorizer().fit(list(texts), list(labels))
    metrics = cat_mod.evaluate(model, corpus.test)
    probs = model.predict_proba([t for t, _ in corpus.test])
    preds = [model.classes_[i] for i in probs.argmax(axis=1)]
    confusions = Counter((get_subcategory(y).label, get_subcategory(p).label)
                         for (_, y), p in zip(corpus.test, preds) if y != p)
    metrics["n_train"] = len(corpus.train)
    metrics["n_classes"] = len(model.classes_)
    metrics["top_confusions"] = [{"true": a, "predicted": b, "count": n} for (a, b), n in confusions.most_common(5)]
    metrics["version"] = cat_mod.MODEL_VERSION
    return metrics


def _anomaly_on(seeds: range, today: datetime) -> dict:
    tp = fp = fn = tn = 0
    by_kind: dict[str, list[int]] = {}
    for s in seeds:
        sc = eval_scenario(s)
        g = generate_group(sc, today)
        txns = [Txn(str(i), e.amount_paisa, get_subcategory(e.subcategory).category, e.subcategory, e.occurred_at,
                    len(e.shares), e.merchant, e.description) for i, e in enumerate(g.expenses)]
        res = score_all(txns, len(sc.members))
        for e, t in zip(g.expenses, txns):
            flagged = res[t.id]["flagged"]
            if e.is_anomaly:
                k = by_kind.setdefault(e.anomaly_kind, [0, 0])
                k[1] += 1
                if flagged:
                    tp += 1
                    k[0] += 1
                else:
                    fn += 1
            elif flagged:
                fp += 1
            else:
                tn += 1
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"groups": len(seeds), "transactions": tp + fp + fn + tn, "injected_anomalies": tp + fn,
            "precision": round(p, 4), "recall": round(r, 4), "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
            "false_positive_rate": round(fp / (fp + tn), 5) if fp + tn else 0.0,
            "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
            "recall_by_kind": {k: round(v[0] / v[1], 3) for k, v in sorted(by_kind.items())}}


def eval_forecast(seeds: range, today: datetime) -> dict:
    rows = []
    for s in seeds:
        g = generate_group(eval_scenario(s), today)
        txns = [SpendTxn(e.amount_paisa, get_subcategory(e.subcategory).category, e.subcategory, e.occurred_at,
                         e.description, e.merchant) for e in g.expenses if not e.is_anomaly]
        b = backtest(txns, today.date())
        if b.get("n_windows"):
            rows.append(b)
    df = pd.DataFrame(rows)
    m = df.mean(numeric_only=True)
    return {
        "groups": len(rows), "windows": int(df["n_windows"].sum()), "horizon_days": 7,
        "mae_7day": round(float(m["mae_7day"])), "rmse_7day": round(float(m["rmse_7day"])),
        "baseline_mean28": {"mae_7day": round(float(m["baseline_mean28_mae_7day"])),
                            "rmse_7day": round(float(m["baseline_mean28_rmse_7day"]))},
        "baseline_lastweek": {"mae_7day": round(float(m["baseline_lastweek_mae_7day"])),
                              "rmse_7day": round(float(m["baseline_lastweek_rmse_7day"]))},
        "mae_improvement_vs_mean28_pct": round((1 - m["mae_7day"] / m["baseline_mean28_mae_7day"]) * 100, 1),
        "weekly_mape": round(float(m["weekly_mape"]), 3), "bias_pct": round(float(m["bias_pct"]), 1),
        "mae_daily": round(float(m["mae_daily"])), "baseline_mae_daily": round(float(m["baseline_mae_daily"])),
        "units": "taka", "version": fc_mod.MODEL_VERSION,
        "note": "Evaluated on normal spending: injected anomalies are removed, as the product excludes unusual one-offs.",
    }


def write_markdown(r: dict) -> None:
    c, a, f = r["categorizer"], r["anomaly"], r["forecast"]
    lines = [
        "# Model evaluation (synthetic-data simulation)",
        "",
        f"Generated {r['generated_at']} by `python -m scripts.evaluate_models`. **All results come from synthetic data** "
        "— they show the methods work as designed on realistic simulated behaviour, not production performance.",
        "",
        "## 1. Expense categorization",
        f"Model `{c['version']}` — {c['n_train']:,} training examples, {c['n_classes']} subcategories. "
        f"Test set: {c['n_test']} examples built only from **merchants and phrasings never seen in training**.",
        "",
        "| Level | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) |",
        "|---|---|---|---|---|",
        f"| Subcategory | {c['subcategory']['accuracy']:.1%} | {c['subcategory']['precision_macro']:.1%} | "
        f"{c['subcategory']['recall_macro']:.1%} | {c['subcategory']['f1_macro']:.1%} |",
        f"| Category | {c['category']['accuracy']:.1%} | {c['category']['precision_macro']:.1%} | "
        f"{c['category']['recall_macro']:.1%} | {c['category']['f1_macro']:.1%} |",
        "",
        f"When the model is confident (probability ≥ {c['low_confidence_threshold']}, {c['confident_share']:.0%} of test "
        f"cases) subcategory accuracy is **{c['accuracy_when_confident']:.1%}**; below that, the app asks the user to confirm.",
        "",
        "Most frequent confusions: " + "; ".join(f"{x['true']} → {x['predicted']} ({x['count']})" for x in c["top_confusions"]),
        "",
        "## 2. Unusual expense detection",
        f"Hybrid model `{a['test']['version'] if 'version' in a['test'] else r['anomaly_version']}`. Weights and the "
        f"threshold ({r['anomaly_threshold']}) were tuned on validation seeds; the test set uses different seeds.",
        "",
        "| Split | Groups | Transactions | Injected anomalies | Precision | Recall | F1 | False-positive rate |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name in ("validation", "test"):
        x = a[name]
        lines.append(f"| {name} | {x['groups']} | {x['transactions']:,} | {x['injected_anomalies']} | {x['precision']:.1%} | "
                     f"{x['recall']:.1%} | {x['f1']:.1%} | {x['false_positive_rate']:.2%} |")
    lines += ["", "Recall by anomaly type (test): " + ", ".join(f"{k} {v:.0%}" for k, v in a["test"]["recall_by_kind"].items()),
              "",
              "## 3. Cash-flow forecast (7-day horizon)",
              f"Rolling-origin backtest over {f['groups']} test groups ({f['windows']} forecast windows). Amounts in taka.",
              "",
              "| Model | MAE (7-day total) | RMSE (7-day total) |",
              "|---|---|---|",
              f"| GroupWise forecast | ৳{f['mae_7day']:,} | ৳{f['rmse_7day']:,} |",
              f"| Baseline: previous 28-day average | ৳{f['baseline_mean28']['mae_7day']:,} | ৳{f['baseline_mean28']['rmse_7day']:,} |",
              f"| Baseline: last week repeated | ৳{f['baseline_lastweek']['mae_7day']:,} | ৳{f['baseline_lastweek']['rmse_7day']:,} |",
              "",
              f"MAE improvement vs the 28-day-average baseline: **{f['mae_improvement_vs_mean28_pct']}%**. Mean absolute "
              f"percentage error of the weekly total: {f['weekly_mape']:.0%}; mean bias {f['bias_pct']:+.1f}% "
              f"(positive = actual spending above forecast). {f['note']}",
              "",
              "## Limitations",
              "- Synthetic data cannot capture every real-world behaviour; production use would need validation on "
              "appropriately governed, anonymised data.",
              "- The anomaly test set contains injected anomalies of known types; novel anomaly types may be missed.",
              "- Forecast error is naturally high for small groups with irregular spending; the app shows an 80% range "
              "and a confidence label rather than a single number.",
              ""]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    t0 = time.time()
    today = local_now()
    result = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "label": "Synthetic-data simulation",
        "categorizer": eval_categorizer(),
        "anomaly": {"validation": _anomaly_on(range(0, 40), today), "test": _anomaly_on(range(100, 140), today)},
        "anomaly_version": anomaly_mod.MODEL_VERSION,
        "anomaly_threshold": anomaly_mod.FLAG_THRESHOLD,
        "forecast": eval_forecast(range(100, 120), today),
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=float), encoding="utf-8")
    write_markdown(result)
    print(json.dumps({k: result[k] for k in ("categorizer", "anomaly", "forecast")}, indent=1, default=float)[:3000])
    print(f"done in {time.time() - t0:.1f}s → {OUT_JSON} and {OUT_MD}")


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
