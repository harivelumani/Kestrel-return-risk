# Kestrel Home — returns risk

## Project overview

Before an order ships, this system estimates how likely it is to be returned and tells a dispatcher what to do. The score comes from a logistic regression trained on past Kestrel orders. A small API serves that frozen model. A single screen calls the API.

## Business problem

Returns are an operating-cost problem. Kestrel wants risky orders flagged before dispatch. The board asked for 95% accuracy. The useful question is whether to intervene, because a false alarm and a missed return do not cost the same thing.

## Dataset

Place the task pack in `Document/` (or set `KESTREL_DATA_DIR`):

- `train.csv`, `test_unlabelled.csv`, `customers.csv`, `products.csv`
- `sample_submission.csv`, `ops-policy.pdf`, `email-thread.txt`, `README.txt`

Those files are client data. They are listed in `.gitignore` and must not be published.

Labeled history, after dropping 651 exact partner-feed copies, is 10,504 orders from 1 April 2025 through 30 June 2026. 1,200 were returned (11.42%). The unlabeled file is 2,096 orders from 1 July 2026 through 30 September 2026.

## Assumptions

- The decision time is just before shipment.
- `customer_prior_orders` and `customer_prior_returns` are the counters on the dispatch snapshot, so they are allowed as inputs. They do not behave like a running total inside this extract.
- A prior return rate of 0 is used when the customer has no prior orders.
- PIN `0` means the address was not captured, on every channel.
- The priced action is the Rs 45 confirmation call. A 24-hour hold is not given a rupee cost, because the policy does not state one.
- Shield orders are scored with everyone else. A high score on a Shield order recommends a call, not a hold.

## Data leakage prevention

Service-event and reverse-pickup fields were fit once as a diagnostic. On the April–June 2026 window that model reached 99.06% accuracy and ROC-AUC 0.997. Those fields are written when a return is approved or after delivery, and the dispatch snapshot does not contain them. The model was discarded. The live score does not use them.

## Feature engineering

Checkout fields, product family and list price, state, Shield, order month, promised delivery days, and the supplied prior-count fields. History rebuilt from earlier rows was tested and did not replace the supplied counts. Details are in `docs/feature_decisions.md`.

## Validation strategy

Train on 1 April 2025–31 March 2026 (8,378 orders). Validate on 1 April 2026–30 June 2026 (2,126 orders, 245 returns). The unlabeled quarter is later and was not used to choose the model or the threshold. A random split was not used.

## Model selection

Logistic regression. HistGradientBoosting was worse on the same split (ROC-AUC 0.761 versus 0.785) and harder to explain. No neural net and no language model.

## Model performance

Temporal validation, logistic regression, supplied history:

| | Accuracy | ROC-AUC | PR-AUC |
|---|---:|---:|---:|
| Selected model at a 0.50 cutoff | 89.51% | 0.785 | 0.411 |
| Majority baseline ("never returned") | 88.48% | 0.50 | 0.115 |

95% accuracy was not achieved. The only run above 95% used post-shipment fields and was discarded. At the 0.50 cutoff the model catches 18% of returns. At the operating threshold of 0.10 it catches 75%, with precision 0.23, and accuracy falls to 67.6% because many non-returns are flagged for a call.

July–September 2026 outcomes are not in this pack. Test-set accuracy is unknown.

## Business threshold

| Score | Level | Action |
|---|---|---|
| Below 0.10 | Low | Normal dispatch |
| 0.10 up to 0.30 | Review | Confirmation call |
| 0.30 or higher | High | Consider hold |

Shield orders use the same score. At Review or High, the action is a confirmation call, not a 24-hour hold.

0.10 had the highest estimated net on the validation grid under the policy's 35% prevention rate. 0.30 is the first grid point where precision exceeded 40%. It is an operations filter, not a priced optimum.

## How to generate predictions

From the project folder, with the task pack in `Document/`:

```bash
python -m pip install -r requirements.txt
python scripts/fit_final.py
python scripts/validate_submission.py
```

`fit_final.py` refits the frozen logistic pipeline on all 10,504 labeled orders and writes `predictions.csv` plus `artifacts/model.joblib`. It does not retune the threshold. `validate_submission.py` prints `PASS` or `FAIL`.

`predictions.csv` is generated locally using the supplied private test data and is intentionally excluded from the public repository. It contains client order IDs. Submit that file through the private assignment channel if the evaluator needs it.

If `artifacts/model.joblib` is already present, you can skip `fit_final.py` and start the API.

## How to run API

```bash
uvicorn api.main:app --reload
```

The service listens on `http://127.0.0.1:8000`. No API key.

## How to run UI

In a second terminal:

```bash
streamlit run ui/app.py
```

The screen posts the form to `POST /predict`. If the API is not running, the screen says the service is unavailable.

## API example

Synthetic order. Not a Kestrel customer record.

```bash
curl -X POST http://127.0.0.1:8000/predict ^
  -H "Content-Type: application/json" ^
  -d "{\"order_placed_at\":\"2026-08-15T10:00:00\",\"sales_channel\":\"web\",\"payment_mode\":\"prepaid_upi\",\"discount_pct\":5,\"qty\":1,\"promised_delivery_days\":4,\"delivery_pincode\":560001,\"is_gift\":\"N\",\"customer_prior_orders\":1,\"customer_prior_returns\":0,\"signup_date\":\"2024-06-01\",\"state\":\"MH\",\"shield_member\":\"N\",\"family\":\"Ceiling Fan\",\"list_price_inr\":3499,\"launch_date\":\"2024-01-01\"}"
```

## Expected output

```json
{
  "risk_score": 0.014913,
  "risk_level": "LOW",
  "recommended_action": "Normal dispatch",
  "reasons": [
    "This customer is not a Shield member. Non-Shield orders have a lower historical return rate.",
    "This is not a gift order.",
    "Ceiling fans have a lower historical return rate."
  ],
  "shield_handling": null
}
```

`risk_score` is the frozen pipeline's probability, rounded to 6 decimals. Higher means a higher chance of return. On the validation window these scores tracked observed return rates closely, except in the top eighth, where the average score (0.42) ran above the observed rate (0.38).

Missing fields and illegal values return HTTP 422 with a short `detail` message. A missing model file returns HTTP 503. The response does not include a stack trace.

## Testing

```bash
python -m unittest tests.test_api tests.test_pipeline -v
python scripts/validate_submission.py
```

## Known limitations

- Validation is one historical quarter, not a live pilot.
- July–September 2026 outcomes are unavailable, so test accuracy is unknown.
- The supplied prior-count fields cannot be reliably reconstructed from this extract, and the model depends on them.
- The Rs 37,208 figure is an estimated validation-window net, not a measured saving.
- 95% accuracy was not achieved without using post-shipment fields.
- A 24-hour hold has a 12% customer-cancel rate in the policy and no stated rupee cost.

## AI tools used

Cursor was used as the development assistant for this project. The prediction system itself is scikit-learn logistic regression. No language model and no paid model API run in the service or the screen. A language model is a poor fit for a small structured table, and the logistic coefficients already support the reasons shown to staff.

## AI/API cost

Rs 0. The service does not call an external model. No API key is required.

## Discarded approaches

Random split, gradient boosting as the selected model, a no-history model, history rebuilt only from earlier orders, raw order value, and an LLM. The service/pickup model (99.06% accuracy) was discarded as leakage. See `docs/discarded_approaches.md`.

## Data privacy

The original Kestrel files are intentionally excluded from Git because they are client-provided data. `Document/`, `predictions.csv`, and `artifacts/` are gitignored. Do not commit the task pack, the score file, or the fitted model. The README example above is synthetic. No `.env` file is required.
