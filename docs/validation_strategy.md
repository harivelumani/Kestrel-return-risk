# Validation strategy

## Why this split

**FACT.** Labeled orders run from 1 April 2025 through 30 June 2026. The unlabeled file runs from 1 July 2026 through 30 September 2026. Order ids increase with time (`KO2600000`–`KO2610503` labeled, `KO2610504`–`KO2612599` unlabeled). There is no shared order id. Tanmay describes the unlabeled file as the most recent orders and as the snapshot the warehouse sees at dispatch.

**ASSUMPTION, and the deployment rule.** The live question is always "given history, score a later order." The validation window has to point the same way. A random split would train on orders from June 2026 and score orders from May 2026. That is not the job.

A random split was not used, even as a secondary score.

## Windows

| Role | Dates | Orders | Returns | Return rate |
|---|---|---:|---:|---:|
| Fit | 1 Apr 2025 – 31 Mar 2026 | 8,378 | 955 | 11.40% |
| Validation | 1 Apr 2026 – 30 Jun 2026 | 2,126 | 245 | 11.52% |
| Final refit, after selection | 1 Apr 2025 – 30 Jun 2026 | 10,504 | 1,200 | 11.42% |
| Unlabeled score period | 1 Jul 2026 – 30 Sep 2026 | 2,096 | unknown | unknown |

The fit and validation counts were asserted in code before any metric was trusted. Nothing in the labeled file falls on or after 1 July 2026.

## Majority baseline

On the validation window, predicting "not returned" for every order is **88.48%** accurate. Precision and recall on returns are 0. A constant score equal to the fit-window return rate (11.40%) has ROC-AUC 0.50 and PR-AUC 0.115, which is the validation base rate.

Accuracy below about 88.5%, or accuracy a point or two above it, does not by itself mean the model is useless or excellent. Ranking and the cost of a call are the relevant comparisons.

## Leakage prevention inside the split

- The preprocessor is fit on the fit window only, then applied to validation.
- No validation row is used to choose a feature that was not already in the frozen list.
- The unlabeled file is not used to choose the model or the threshold. It is scored once, after both are frozen.
- Rebuilt history, used only in a diagnostic, looks backward in time. A prior return counts only when that earlier order's pickup timestamp is already before the order being scored. The current label is not read.
- Gradient boosting is fit with early stopping off, so it does not hold out a random slice of the fit window.

## Thresholds

Operating points are chosen on the validation window only. The grid is 0.05, 0.08, 0.10, 0.11, 0.12, 0.15, 0.20, 0.25, 0.30, and 0.50. See `business_economics.md` for the rupee comparison.

## Limitations

- One cut in time, not a rolling backtest. Three months of validation can move with season or a promotion we cannot see.
- The prior-return column is not a reliable running total. Part of the validation score depends on it.
- Scores on July–September 2026 have no labels here, so there is no test-set accuracy to report.
- Calibration is checked on the same validation window that is used for the threshold. It is not a second, untouched calibration set.
