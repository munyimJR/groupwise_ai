# Model validation: baselines, ablations, calibration, leakage checks

Generated 2026-10-07 03:41 UTC by `python -m scripts.validate_models`. Data: behavior-driven **synthetic** groups (separate seeds for tuning and testing) and a small hand-written stress set. Real-user validation comes from the pilot (`scripts/pilot_metrics.py`). Intervals are 95% bootstrap confidence intervals.

## What counts as machine learning here

| Component | Kind | Learned from data? |
|---|---|---|
| Expense categorizer | **Trained ML**: TF-IDF features + logistic regression | Yes, supervised |
| Unusual-expense detector | **ML + statistics**: Isolation Forest (unsupervised, fitted per group) combined with robust z-scores and rules | Isolation Forest yes; rules no |
| Cash-flow forecast | **Statistical time-series model**: exponential smoothing with weekday/month factors and recurring-bill detection | Fitted per group |
| Goal likelihood | **Simulation**: bootstrap Monte-Carlo of the group's own contributions | No training |
| Spending drivers, group dynamics, health score | **Deterministic analytics** | No |
| Ask GroupWise | **LLM** for wording only, numbers verified | Pre-trained, not trained by us |

So GroupWise has **two learned models** (categorizer, Isolation Forest) and **one fitted statistical forecaster**, plus simulation and analytics. Earlier material that said “five ML models” overstated this.

## 1. Expense categorizer

**Splits.** 1,044 training and 244 test examples, 34 subcategories. Per subcategory, 25% of merchants and 25% of phrasing templates are held out. Every test example uses a held-out merchant, a held-out phrasing, or both. The regularization strength was chosen by 5-fold cross-validation **on the training split only** (C = 30; CV accuracy by C: 1.0: 92.7%, 3.0: 94.6%, 12.0: 95.0%, 30.0: 95.1%).

**Leakage checks.** Test texts that also appear verbatim in training: **1**. Excluded from all test metrics: the merchant knowledge base contains held-out merchants, so using it at test time would leak.

**Baselines and ablations (same test set):**

| System | Subcategory accuracy (95% CI) | Macro F1 | Category accuracy |
|---|---|---|---|
| Majority class | 8.2% (4.9%–11.5%) | 0.4% | 22.9% |
| Keyword rules (simple baseline) | 65.6% (59.0%–71.7%) | 67.8% | 70.9% |
| Naive Bayes (word counts) | 74.6% (69.3%–79.9%) | 76.3% | 79.1% |
| TF-IDF words only + LR | 79.1% (74.2%–83.6%) | 80.3% | 82.4% |
| TF-IDF characters only + LR | 81.6% (76.6%–86.1%) | 79.6% | 84.0% |
| GroupWise as deployed (C = 12) | 80.3% (74.6%–85.2%) | 79.7% | 83.2% |
| GroupWise, CV-selected C = 30 | 81.6% (76.6%–86.1%) | 81.2% | 84.0% |

**Calibration.** Expected calibration error **0.117** (Brier 0.257). The model is mostly under-confident: in the middle bins it is right far more often than its stated confidence. One temperature fitted on out-of-fold training predictions (T = 0.6) changes the test error to **0.029** (Brier 0.232). The app auto-accepts a category only above a confidence threshold and asks the person otherwise:

| Confidence threshold | Share auto-accepted | Accuracy when auto-accepted |
|---|---|---|
| 0.3 | 83.6% | 92.6% |
| 0.45 | 77.0% | 96.8% |
| 0.6 | 70.1% | 98.2% |
| 0.8 | 54.1% | 100.0% |

| Confidence bin | n | Mean confidence | Accuracy |
|---|---|---|---|
| 0.0–0.1 | 15 | 0.08 | 0.13 |
| 0.1–0.2 | 14 | 0.15 | 0.21 |
| 0.2–0.3 | 11 | 0.25 | 0.46 |
| 0.3–0.4 | 11 | 0.35 | 0.46 |
| 0.4–0.5 | 11 | 0.45 | 0.73 |
| 0.5–0.6 | 11 | 0.56 | 0.73 |
| 0.6–0.7 | 23 | 0.66 | 0.96 |
| 0.7–0.8 | 16 | 0.75 | 0.88 |
| 0.8–0.9 | 38 | 0.85 | 1.00 |
| 0.9–1.0 | 94 | 0.96 | 1.00 |

**Hand-written stress set** (70 descriptions written outside the generator's templates, never used for training or tuning): GroupWise 91.4% (CI 84.3%–97.1%), keyword rules 68.6%. Small sample, so the interval is wide. Example errors: “ordered khichuri online for the flat” → Electronics (should be Food Delivery); “toothpaste soap and detergent from super shop” → Household Supplies (should be Supermarket); “flexiload 100 taka” → Cafe & Snacks (should be Mobile Recharge); “pc game top up” → Fuel (should be Gaming).

## 2. Unusual-expense detector

**Splits.** Tuning seeds 0–39, test seeds 100–139. Every variant's threshold is chosen on the tuning seeds, then scored once on the test seeds. F1 intervals come from a bootstrap over groups.

| Variant | Threshold | Precision | Recall | F1 (95% CI) |
|---|---|---|---|---|
| Rule: amount > 3x the group's median for that subcategory | 1.05 | 62.0% | 43.7% | 51.3% (45.4%–58.5%) |
| Robust z-score only (amount vs subcategory and group) | 0.2 | 67.5% | 55.0% | 60.6% (53.4%–67.1%) |
| Isolation Forest only | 0.35 | 53.2% | 43.7% | 48.0% (42.9%–53.5%) |
| Rules only (night-time, rare category, duplicate) | 0.2 | 79.9% | 72.3% | 75.9% (70.9%–80.4%) |
| Hybrid without Isolation Forest | 0.6 | 94.7% | 85.7% | 90.0% (86.0%–93.5%) |
| GroupWise hybrid (all signals) | 0.6 | 91.0% | 96.5% | 93.7% (90.5%–96.0%) |

**Operating point (validation seeds):** threshold 0.4: P 62.9%, R 96.3%; threshold 0.5: P 71.8%, R 96.3%; threshold 0.6: P 89.6%, R 92.9%; threshold 0.7: P 95.1%, R 80.1%; threshold 0.8: P 95.9%, R 57.7%

**Temporal leakage check.** Batch evaluation compares each expense with the group's whole history, including later expenses. The live app only sees the past. Over the last 28 days of each test group (43 injected anomalies): **past-only scoring** P 88.9%, R 93.0%, F1 90.9% versus batch scoring F1 94.2% on the same transactions. The past-only number is the one that reflects the product.

## 3. Cash-flow forecast (7-day total)

**Splits.** Rolling origin: 8 weekly cut-offs per group; each forecast is fitted only on data before its cut-off and scored on the next 7 days. 160 windows over test seeds 100–119.

| System | MAE (95% CI across groups) |
|---|---|
| Mean of previous 28 days | ৳8,261 (৳6,318–৳10,067) |
| Last week repeated | ৳9,122 (৳7,225–৳11,011) |
| Same weekday, 4-week average | ৳8,261 (৳6,432–৳10,063) |
| GroupWise without recurring bills | ৳6,512 (৳5,248–৳7,704) |
| GroupWise without weekday/month factors | ৳3,667 (৳3,004–৳4,286) |
| GroupWise without recency weighting | ৳3,394 (৳2,816–৳4,054) |
| GroupWise forecast | ৳3,625 (৳2,966–৳4,305) |

Improvement over the 28-day-average baseline: **56.1%** (95% CI 40.7–67.8%).

**Range calibration.** Before tuning, the app's 80% range contained the actual 7-day total in only 65.0% of 160 test windows: too narrow, because each group has only about 8 past windows to learn its errors from. Fix: 10th-90th percentile of the group's own backtest errors, widened 1.75x; the widening was chosen on validation seeds 0-19 (80.5% coverage there). Coverage on the untouched test seeds is now **76.9%** (target 80%). Weekly group spending is volatile, so an honest 80% range is wide.

**Leakage check.** Passing future transactions to the forecaster changes its forecast: **no** (it fits only on data before the cut-off).

## Limits

- Everything above is synthetic or hand-written. It shows the methods work and beat simple rules on realistic simulated behavior; it does not prove performance on real users. The pilot measures that directly: AI category acceptance, flagged-expense review outcomes, and forecast error on real groups.
- The anomaly test set contains injected anomaly types we designed; new real-world anomaly types may be missed.
