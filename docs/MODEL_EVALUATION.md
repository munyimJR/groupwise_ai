# Model evaluation (synthetic-data simulation)

Generated 2026-10-03 21:48 UTC by `python -m scripts.evaluate_models`. **All results come from synthetic data** — they show the methods work as designed on realistic simulated behaviour, not production performance.

## 1. Expense categorization
Model `tfidf-logreg-1.1` — 1,044 training examples, 34 subcategories. Test set: 245 examples built only from **merchants and phrasings never seen in training**.

| Level | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) |
|---|---|---|---|---|
| Subcategory | 80.4% | 83.3% | 78.8% | 79.7% |
| Category | 83.3% | 80.2% | 75.1% | 76.9% |

When the model is confident (probability ≥ 0.45, 73% of test cases) subcategory accuracy is **97.8%**; below that, the app asks the user to confirm.

Most frequent confusions: Household Supplies → Electronics (2); Clothing → Electronics (2); Electronics → Household Supplies (2); Restaurant → Cafe & Snacks (1); Fast Food → Cafe & Snacks (1)

## 2. Unusual expense detection
Hybrid model `iforest-robust-1.2`. Weights and the threshold (0.6) were tuned on validation seeds; the test set uses different seeds.

| Split | Groups | Transactions | Injected anomalies | Precision | Recall | F1 | False-positive rate |
|---|---|---|---|---|---|---|---|
| validation | 40 | 14,935 | 241 | 85.5% | 93.0% | 89.1% | 0.26% |
| test | 40 | 13,690 | 231 | 88.7% | 95.2% | 91.9% | 0.21% |

Recall by anomaly type (test): amount 88%, category 93%, duplicate 100%, time 100%

## 3. Cash-flow forecast (7-day horizon)
Rolling-origin backtest over 20 test groups (160 forecast windows). Amounts in taka.

| Model | MAE (7-day total) | RMSE (7-day total) |
|---|---|---|
| GroupWise forecast | ৳2,902 | ৳3,528 |
| Baseline: previous 28-day average | ৳7,673 | ৳9,235 |
| Baseline: last week repeated | ৳9,447 | ৳12,477 |

MAE improvement vs the 28-day-average baseline: **62.2%**. Mean absolute percentage error of the weekly total: 28%; mean bias +7.1% (positive = actual spending above forecast). Evaluated on normal spending: injected anomalies are removed, as the product excludes unusual one-offs.

## Limitations
- Synthetic data cannot capture every real-world behaviour; production use would need validation on appropriately governed, anonymised data.
- The anomaly test set contains injected anomalies of known types; novel anomaly types may be missed.
- Forecast error is naturally high for small groups with irregular spending; the app shows an 80% range and a confidence label rather than a single number.
