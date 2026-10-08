# Discarded approaches

Only items that were run, or explicitly considered and not run, are listed. No metric below was filled in after the fact.

## Export-day service and pickup fields

- **Why considered.** They are columns on the order extract, and four delivery notes say to keep them and to headline validation accuracy.
- **What happened.** A logistic model on `has_pickup` and `last_service_event_type` only, same time split as everything else: ROC-AUC 0.997, PR-AUC 0.977, accuracy 99.06% at 0.50 (TN 1,864, FP 17, FN 3, TP 242).
- **Why discarded.** The policy says those fields are written when a return is approved or when service happens after delivery. Train is an export-day snapshot. The dispatch file we have to score has no pickup times, no `REVERSE_PICKUP`, and a service value (`INSTALL_BOOKED`) that never appears in train. The 99% figure does not survive contact with the test snapshot.
- **Lesson.** A very high accuracy on this file is a reason to suspect leakage, not a reason to brief the board.

## Random train/validation split

- **Why considered.** It is the default in most libraries.
- **What happened.** Not run. The unlabeled period is strictly later (1 July–30 September 2026), and labeled order ids already follow time.
- **Why discarded.** A random split would train on later orders and score earlier ones. That is the wrong direction for dispatch.
- **Lesson.** The 88.48% majority accuracy and every model metric in `model_experiments.md` are temporal.

## HistGradientBoosting as the selected model

- **Why considered.** A tree model can pick up channel × Shield × family patterns without hand-built interactions.
- **What happened.** With the same features and the same split: ROC-AUC 0.761, PR-AUC 0.367, Brier 0.088, best estimated net Rs 34,825. Logistic was 0.785, 0.411, 0.085, and Rs 37,208.
- **Why discarded.** It was worse on ranking, calibration, and the policy arithmetic, and harder to explain. No extra library was added to try a third booster.
- **Lesson.** On 8,000 rows and a handful of checkout fields, the linear model was enough.

## Dropping history entirely

- **Why considered.** Stated prior counts do not increase with time inside this extract, so they might be noise or a leak.
- **What happened.** Logistic ROC-AUC fell from 0.785 to 0.734 and PR-AUC from 0.411 to 0.294.
- **Why discarded as the primary model.** The loss is large. The fields stay, with the limitation written down. They were not "cleaned" into something the file does not support.
- **Lesson.** A consistency failure and a predictive failure are different findings. Here we have the first, and we measured the second.

## History rebuilt only from earlier orders

- **Why considered.** If the CRM counters are wrong, a backward count might be the honest replacement. A return was counted only when its pickup timestamp was already before the order being scored.
- **What happened.** Logistic ROC-AUC 0.736 and PR-AUC 0.291, in line with the no-history model. Correlation with the supplied prior-return count is 0.12.
- **Why discarded.** It does not replace the snapshot field. Using it *as well as* the snapshot field would mix two definitions of the same idea.
- **Lesson.** The signal in `customer_prior_returns` is not recoverable from this extract. Operations should confirm what that CRM field actually contains.

## Order value as its own feature

- **Why considered.** It is the payment amount.
- **What happened.** Outside October 2025 it matches list price × quantity × (1 − discount) exactly. October 2025 matches that formula × 100, which fits the unchecked festive gateway.
- **Why discarded.** After that check, the column adds no information beyond price, quantity, and discount.
- **Lesson.** The October spike is a unit error, not a demand shock.

## Raw PIN, city, warranty, model name, delivery notes

- **Why considered.** They are known before dispatch.
- **What happened.** PIN has 3,479 levels. Warranty is 24 months for two families and 12 for the rest. Notes are repeated templates; common templates differ by only a few points of return rate. City is a finer cut of state. None of these were put through a separate model bake-off.
- **Why discarded.** They either repeat a column already kept or add cardinality without a clear rate gap. A missing-address flag was kept instead of the raw PIN.
- **Lesson.** "Known at dispatch" is necessary, not sufficient.

## LLM, paid API, deep learning

- **Why considered.** The brief allows an optional model API and asks for reasons a person can read.
- **What happened.** Not run. No API key, no deep model.
- **Why discarded.** The inputs are a small table. Logistic coefficients already point at COD, prior returns, promised days, Shield, and product family. A language model would add cost and a failure mode without a label to fine-tune on.
- **Lesson.** The service, when it is built, has to run with the scikit-learn pipeline alone.

## Chasing 95% accuracy

- **Why considered.** Ritu has told the board that number.
- **What happened.** Not pursued by changing the split, the label, or the test file. The eligible ceiling on this validation window, at a 0.50 cutoff, is 89.51%.
- **Why discarded.** The leaky service model is the only way this pack produces a 95% accuracy, and it answers a different question ("has the return already been booked?").
- **Lesson.** Report 89.5% at the conservative cutoff, 67.6% at the call cutoff, and the estimated net. Do not report 95%.
