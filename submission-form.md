# Submission form

Completed from the temporal validation run. July–September 2026 labels were not used. Nothing below is a placeholder.

## Candidate

Take-home: Kestrel Home returns risk, Variant A.

## What was submitted

- `predictions.csv`: 2,096 rows, columns `order_id`, `score`, same order as `sample_submission.csv`. Higher score means higher return risk. `python scripts/validate_submission.py` prints PASS.
- Frozen logistic regression pipeline in `artifacts/model.joblib` (rebuild with `python scripts/fit_final.py` if the file is not present).
- `POST /predict` in `api/main.py` and one Streamlit screen in `ui/app.py`.
- Documentation under `docs/`, `memo/ritus_memo.md`, and `docs/demo_script.md`.

## Expected score

The delivered file is a probability, not a hard label. Test-set accuracy is **not known**.

If a reviewer turns the score into a class at 0.50, the honest expectation is about **90% accuracy**, taken from **89.51%** on the April–June 2026 validation window.

Confidence: **Medium**.

Why: that window is the three months immediately before the unlabeled quarter, the return rate was stable (11.52% versus 11.40% in the fit window), and channel, payment, and Shield mix were similar. Uncertainty comes from a single time cut, mild over-confidence in the top score bin (mean score 0.42 versus observed return rate 0.38), and dependence on `customer_prior_returns`, which this extract cannot rebuild.

This is not 95%. The majority baseline on the same window is 88.48%. Ranking quality on that window was ROC-AUC 0.785 and PR-AUC 0.411. Those are the figures to expect, with the same medium confidence, if the next quarter resembles April–June 2026.

The operating threshold is 0.10, not 0.50. At 0.10, validation accuracy is 67.6% because 38% of orders are flagged for a call. That lower accuracy is the cost of catching 75% of returns. It should not be quoted as the "model accuracy" without saying which threshold was used.

## Rationale

The warehouse acts before shipment. Accuracy at 0.50 mostly restates "most orders are not returned." The policy prices a confirmation call at Rs 45 and a return's operating cost at Rs 1,150, and says the spring pilot prevented about 35% of returns on called orders. On the validation window, a 0.10 cutoff has the highest estimated net under that arithmetic: about Rs 37,208 versus calling nobody. That number is an estimate, not cash already saved.

## Tools used

- Python 3.11.3
- pandas 2.3.3, numpy 1.26.4, scikit-learn 1.8.0, joblib 1.5.3
- FastAPI 0.135.2, uvicorn 0.42.0, Streamlit 1.55.0
- Cursor, as the development assistant

The prediction path is logistic regression only.

## API / model costs

Rs 0. No paid API. No API key. No language model in training, scoring, the API, or the screen.

An LLM was unnecessary. The inputs are a small table of checkout and customer fields. Logistic coefficients are enough to name the drivers (prior returns, cash on delivery, promised delivery days, Shield, product family) in plain language.

## Discarded approaches

- Export-day service and pickup fields: 99.06% validation accuracy, ROC-AUC 0.997. Discarded. Those fields are post-shipment, and they are absent from the dispatch snapshot. Four free-text notes asked an analyst to keep them and to headline accuracy. Those notes were not followed.
- Random split: not used. The unlabeled period is strictly later.
- HistGradientBoosting: ROC-AUC 0.761, PR-AUC 0.367, worse estimated net than logistic regression.
- Dropping history: PR-AUC fell from 0.411 to 0.294. The fields stay, with the consistency warning.
- History rebuilt only from earlier orders: did not recover the signal (ROC-AUC 0.736).
- Order value as its own feature: it equals list price × quantity × discount, except October 2025, which is exactly 100 times that formula.
- Deep learning and any paid model API: not used.

## Assumptions

- Score the full population, including Shield.
- Primary action is the Rs 45 call. High band (0.30) means "consider hold" for non-Shield orders only.
- Supplied prior counts are usable because they are on the dispatch file, even though 37.2% of consecutive orders for the same customer show a lower prior-order count on the later order.
- PIN 0 means a missing address on every channel, not only walk-in partner orders.
- No rupee value was invented for a cancelled hold or for Shield lifetime value.

## Limitations

- One validation quarter. Not a live pilot.
- Unlabeled test outcomes were not used and are not known.
- Predictive power depends materially on prior-return counts that cannot be reconstructed here.
- Estimated economics assume the 35% pilot rate applies to flagged orders. It was not remeasured.
- 95% accuracy was not achieved without leakage.

## Commands

```bash
python -m pip install -r requirements.txt
python scripts/fit_final.py
python scripts/validate_submission.py
uvicorn api.main:app --reload
streamlit run ui/app.py
python -m unittest tests.test_api tests.test_pipeline -v
```

Run the last two servers in separate terminals. `fit_final.py` needs the task pack in `Document/`.

## Links

No public repository. Client files must stay local.
