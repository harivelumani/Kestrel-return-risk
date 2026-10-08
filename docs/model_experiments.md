# Model experiments

All scores below are on the April–June 2026 validation window (2,126 orders, 245 returns) after a fit on April 2025–March 2026 only. Seed 42. No unlabeled row was used.

Preprocessing for every candidate: median impute and standardise numeric fields; most-frequent impute and one-hot encode categories. Logistic regression: L2, `C=1`, `lbfgs`, no class weight. HistGradientBoosting: 200 iterations, learning rate 0.08, max depth 4, minimum leaf 30, L2 0.1, early stopping off.

## Ranking and the 0.50 cutoff

| Experiment | Model | History | ROC-AUC | PR-AUC | Brier | Accuracy | Precision | Recall | F1 | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E0 | Majority class | None | 0.500 | 0.115 | 0.102 | 0.885 | 0.000 | 0.000 | 0.000 | 1,881 | 0 | 245 | 0 |
| E1 | Logistic regression | Supplied prior counts | 0.785 | 0.411 | 0.085 | 0.895 | 0.662 | 0.184 | 0.288 | 1,858 | 23 | 200 | 45 |
| E2 | HistGradientBoosting | Supplied prior counts | 0.761 | 0.367 | 0.088 | 0.892 | 0.625 | 0.163 | 0.259 | 1,857 | 24 | 205 | 40 |
| E3 | Logistic regression | None | 0.734 | 0.294 | 0.093 | 0.889 | 0.680 | 0.069 | 0.126 | 1,873 | 8 | 228 | 17 |
| E4 | HistGradientBoosting | None | 0.724 | 0.293 | 0.093 | 0.884 | 0.472 | 0.069 | 0.121 | 1,862 | 19 | 228 | 17 |
| E5 | Logistic regression | Rebuilt from earlier orders | 0.736 | 0.291 | 0.093 | 0.887 | 0.591 | 0.053 | 0.097 | 1,872 | 9 | 232 | 13 |
| E6 | HistGradientBoosting | Rebuilt from earlier orders | 0.707 | 0.278 | 0.094 | 0.886 | 0.533 | 0.065 | 0.116 | 1,867 | 14 | 229 | 16 |

E0 accuracy is the hard rule "never returned." Its ROC-AUC is 0.5 because the score is a constant (the fit-window return rate, 11.40%). PR-AUC equals the validation base rate, 0.115.

E1 at 0.50 is 89.51% accurate. That is 1.0 point above the majority rule and 5.5 points short of 95%. Recall at 0.50 is 18.4%: 45 of 245 returns flagged, 200 missed.

## With and without history

| | ROC-AUC | PR-AUC | Best estimated net on the grid |
|---|---:|---:|---:|
| E1 logistic, supplied history | 0.785 | 0.411 | Rs 37,208 at 0.10 |
| E3 logistic, no history | 0.734 | 0.294 | Rs 30,710 at 0.11 |
| E5 logistic, rebuilt history | 0.736 | 0.291 | Rs 31,708 at 0.11 |

**What we learned.** Dropping the stated prior-count fields costs about 0.05 ROC-AUC and 0.12 PR-AUC. The rebuilt history, which uses only earlier orders and only pickups that had already been timestamped, does not get that performance back. The logistic coefficient on `customer_prior_returns` is +0.59. Coefficients on `customer_prior_orders` and `prior_return_rate` are about 0.02 and −0.04. The dependence is specifically the stated prior-return count.

**Decision.** Keep E1. State the dependence and the failed consistency check in the leakage note. Do not pretend the column was verified as a running total.

## Selected model at the call threshold

E1, threshold 0.10.

| | |
|---|---|
| Accuracy | 0.676 |
| Precision | 0.226 |
| Recall | 0.747 |
| F1 | 0.347 |
| Flagged | 810 / 2,126 (38.1%) |
| TP, FP, FN, TN | 183, 627, 62, 1,254 |
| Est. call cost | Rs 36,450 |
| Est. return cost avoided | Rs 73,658 |
| Est. net | Rs 37,208 |

The full grid is in `business_economics.md`. Confusion at the high-band cutoff of 0.30: TP 84, FP 113, FN 161, TN 1,768. Precision 0.426, recall 0.343, 197 orders flagged (9.3%).

## Calibration of E1

Eight equal-count bins on the validation scores. **FACT from this run:** low and middle scores match the observed return rate closely. The top eighth is a bit hot.

| Mean score | Observed return rate | Orders |
|---:|---:|---:|
| 0.016 | 0.015 | 266 |
| 0.031 | 0.026 | 266 |
| 0.045 | 0.042 | 265 |
| 0.064 | 0.079 | 266 |
| 0.087 | 0.075 | 266 |
| 0.123 | 0.121 | 265 |
| 0.193 | 0.184 | 266 |
| 0.422 | 0.380 | 266 |

Brier score 0.085, versus 0.102 for the constant baseline. A score near 0.10 can be read as about a 10% chance of return. Scores above about 0.25 should be read as "high relative to other orders," not as exact probabilities. The top of the range reaches 0.98 on some rows; the top bin as a whole returned at 38%, not at 42%.

Largest logistic directions, after scaling numeric inputs and one-hot encoding categories (these are not clean odds ratios, because every category is coded and L2 shrinks them):

- Higher risk: COD (+0.62), stated prior returns (+0.59), longer promised delivery (+0.43), robot vacuum (+0.27), higher discount (+0.24), higher list price (+0.24), Shield (+0.12 versus −0.81 on non-Shield).
- Lower risk: prepaid UPI, ceiling fan, mixer grinder, partner outlet.

## Why this model

1. Best validation ROC-AUC and PR-AUC of the eligible models.
2. Best estimated net on the policy arithmetic.
3. Better Brier score than boosting, so the score is the more usable probability.
4. Coefficients can be turned into employee-facing reasons later without an explainability library.
5. HistGradientBoosting did not win on any of those points (ROC-AUC 0.761, PR-AUC 0.367, best net Rs 34,825).

## 95% target

Not reached. The best eligible accuracy on the grid is 89.51%, at the 0.50 cutoff, where the model barely beats "never returned." The operating point we would actually use is less accurate and more useful, because it catches 75% of returns and has a higher estimated net. A model that reads export-day service fields scores 99.1% accuracy on this same window. That model is leakage. It is recorded under discarded approaches and was not used to score July–September 2026.

## Final refit

After the table above was frozen, the same logistic pipeline was refit on all 10,504 labeled orders and applied once to the 2,096 unlabeled orders. `predictions.csv` has columns `order_id`, `score`, in the sample file's order. Validation script: PASS. Scores run from 0.004 to 0.974, mean 0.107. That mean is a sanity check that the file is not a constant. It is not a test-set accuracy.

Machine: Python 3.11.3, numpy 1.26.4, pandas 2.3.3, scikit-learn 1.8.0. Commands: `python scripts/run_experiments.py`, then `python scripts/fit_final.py`, then `python scripts/validate_submission.py`.
