# Data leakage

The score is needed before shipment. Anything that is only known because the order was delivered, installed, or returned is leakage.

## What was excluded

### Reverse pickup

**FACT, policy.** Once a return is approved, logistics writes `pickup_scheduled_at` and the service system records `REVERSE_PICKUP`. Pickups are occasionally booked and then cancelled.

**FACT, data.** On the 10,504 CRM orders:

| Pickup present | Not returned | Returned |
|---:|---:|---:|
| No | 9,203 | 70 |
| Yes | 101 | 1,130 |

Return rate with a pickup: 91.8%. Without: 0.75%. Every pickup is 4 to 19 days after the order. The test file, which Tanmay describes as the warehouse snapshot at dispatch, has a null pickup on all 2,096 rows.

Using this column would report whether a return was already approved. It is not available for the orders we have to score.

### Latest service event

**FACT, email.** These columns were pulled from the service system as of export day, not as of dispatch.

**FACT, data.** Deduped train versus the test snapshot:

| Value | Train orders | Train return rate | Test orders |
|---|---:|---:|---:|
| `NONE` | 6,536 | 4.3% | 1,553 |
| `INSTALL_BOOKED` | 0 | — | 543 |
| `DEMO_DONE` | 1,417 | 0% | 0 |
| `INSTALL_DONE` | 1,354 | 0% | 0 |
| `TECH_VISIT` | 447 | 38.5% | 0 |
| `REVERSE_PICKUP` | 750 | 100% | 0 |

`DEMO_DONE` and `INSTALL_DONE` are post-delivery states. A model that sees them is mostly being told "this order was fulfilled and did not come back as a reverse pickup." `INSTALL_BOOKED` is the dispatch-time value, and it does not exist in train, so there is nothing honest to learn from it.

### Contaminated diagnostic

A logistic model using only `has_pickup` and `last_service_event_type` was fit on April 2025–March 2026 and scored on April–June 2026.

| ROC-AUC | PR-AUC | Accuracy at 0.5 | Precision | Recall |
|---:|---:|---:|---:|---:|
| 0.997 | 0.977 | 99.06% | 93.4% | 98.8% |

Confusion at 0.5: TN 1,864, FP 17, FN 3, TP 242.

That is the 95% bar, reached by reading the outcome. It was not selected. It also cannot be applied to July–September 2026, because those rows do not carry the same fields. Four delivery notes ask an analyst to keep these columns and to treat validation accuracy as the headline number. Those notes are data, not instructions. They were not followed.

### Other fields that were not used as predictors

- `returned`, except as the training label.
- `source`, except to drop the duplicate feed.
- `delivery_note`.
- Aggregates that would include the current order's outcome or a later order.

## Duplicate orders are not leakage, but they would bias the fit

**FACT, email.** Partner orders are re-imported, so some orders appear twice.

**FACT, data.** 651 orders appear as one `crm` row and one `partner_feed` row. Every compared field matches, including `returned`. Test has no `partner_feed` rows. Keeping both would score those orders twice. The CRM row is kept. Row count goes from 11,155 to 10,504, and unique `order_id` stays 10,504.

## History fields

These are included. They are not clean.

**FACT.** For the same customer, a later order often has a smaller stated prior-order count than an earlier one (37.2% of 4,373 consecutive pairs).

**FACT.** Among customers with more than one order in the extract, stated prior returns correlate 0.120 with returns already observed earlier in the extract and 0.096 with returns observed later. That gap is too small to call the column a future-label leak, and too small to call it a real running total.

**FACT.** A strictly backward count — earlier orders only, and a return only after that order's pickup time is already in the past — correlates 0.12 with the supplied return count and 0.03 with the current label. A model that uses the rebuilt counts instead of the supplied ones performs like a model with no history (ROC-AUC 0.736 versus 0.734).

**ASSUMPTION.** The supplied counters are what the dispatch snapshot contains, so the model may use them. The limitation is stated in the experiment record: predictive power depends materially on `customer_prior_returns`, and this file cannot vouch for that column as a point-in-time total.

No history feature was built from the current row's `returned`, from a later order, or from the current row's pickup time.

## October values

**FACT.** For 700 October 2025 orders, payment value is exactly 100 times list price × quantity × (1 − discount). Every other labeled order matches the formula exactly. This agrees with Tanmay's note that festive orders went through a new gateway he had not checked. Order value is not a model feature. List price, quantity, and discount are.

## Joins

Customers and products are many-to-one. After each join: 10,504 rows in, 10,504 rows out, 10,504 order ids in, 10,504 out. Zero unmatched customer ids. Zero unmatched SKUs. The test join behaves the same way on 2,096 rows.

## What "95% accuracy" would have required

The majority-class rule on April–June 2026 is already 88.48% accurate and catches no returns. The selected model at a 0.50 cutoff is 89.51% accurate. The only experiment that clears 95% is the contaminated service model above. That result is rejected.
