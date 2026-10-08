# Demo script

Three minutes. No slides. Record the terminal and the one screen.

## 0:00–0:30 — Problem and data

Kestrel wants a flag before dispatch because returns are the hole in the P&L. The policy cost of handling a return is Rs 1,150 on top of the refund. A confirmation call costs Rs 45. The labeled file is April 2025 through June 2026, about 10,500 orders after removing duplicate partner-feed rows, and about 11% were returned. The file we score is July through September 2026 and has no outcomes.

## 0:30–1:00 — Temporal validation and baseline

Show `docs/validation_strategy.md` only if needed, otherwise say it. The model was trained on orders through March 2026 and checked on April through June 2026, which is the same direction as deployment: past predicting future. Predicting "not returned" for everyone is already 88.48% accurate and catches no returns. That is the baseline.

## 1:00–1:30 — What was tried

A logistic regression and one gradient-boosting model, with and without the customer's stated prior returns. Logistic regression won: 89.51% accuracy at a 0.50 cutoff, ROC-AUC 0.785, PR-AUC 0.411. Boosting was a bit worse. Dropping prior returns hurt the ranking. No language model. The useful cutoff is not 0.50. At 10% predicted risk we flag the order for a call. That catches about three quarters of validation returns. Accuracy at that cutoff is lower, about 68%, because we are choosing to review more orders.

## 1:30–2:00 — What was thrown away

A model that used the service-event and reverse-pickup columns scored 99.06% on the same validation window. Those columns are written when a return is approved or after delivery. The warehouse file we have to score does not have them. That model was discarded. So was a random split, because it would train on the future and score the past. We also did not chase 95% by changing the split.

## 2:00–2:40 — Live API and screen

API is already running (`uvicorn api.main:app --reload`). The screen is `streamlit run ui/app.py`.

Enter a synthetic order, not a real customer: cash on delivery, a Shield member, an air fryer, one prior order and no prior return. Submit. Show the percentage, the level, the reasons, and the action. Point out that a Shield order at high risk still says confirmation call, not a 24-hour hold.

If time allows, change Shield to No and payment to prepaid UPI and submit again so the level and the action both change. Same order twice must show the same score.

## 2:40–3:00 — Result and limit

Recommend a one-week call pilot at the 10% line. Estimated net on the validation quarter is about Rs 37,208. Say clearly that this is an estimate, not savings already banked, and that 95% was not hit without using information the warehouse does not have yet. We still need the desk to confirm what the prior-return counter means.
