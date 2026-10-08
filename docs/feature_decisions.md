# Feature decisions

## Would dispatch know this?

The prediction is made when the warehouse is about to ship. A feature is eligible only if a Kestrel employee could know it then.

| Feature | Known immediately before dispatch? | Decision |
|---|---|---|
| Channel, payment mode, discount, quantity, promised days, gift flag | Yes. Captured at checkout. | Included |
| List price, family, product age | Yes. Product master. | Included |
| State, Shield flag | Yes. Customer master. | Included |
| Tenure, and a flag when signup is after the order | The signup date is on the customer master. **FACT:** it is sometimes after the order, so tenure is blank in that case rather than negative. | Included |
| Missing-address flag | Yes. PIN `0` is already how the export marks a missing address. | Included |
| Order month | Yes. It is the placement month. | Included |
| `customer_prior_orders`, `customer_prior_returns`, prior return rate | **ASSUMPTION:** yes, because both columns are on the dispatch snapshot and the README defines them as counts before this order. They fail a consistency check against this file. See below. | Included in the primary model. Removed in a second experiment. |
| City | Yes, but 18 sparse levels and state already covers region. | Excluded |
| Raw PIN | The PIN is known, but there are 3,479 distinct values in train. | Excluded. Missing-address flag kept. |
| Raw delivery note | Ordinary notes are known. They are short templates with little difference in return rate. Four notes are instructions to an analyst. | Excluded |
| Order value | Known, and exactly determined by list price, quantity, and discount once October 2025 is divided by 100. | Excluded as redundant |
| Warranty, model name | Known, and repeated by family or SKU. | Excluded |
| `source` | Not an order attribute. It marks the re-import. | Used only to drop 651 duplicate rows |
| `last_service_event_type`, `pickup_scheduled_at` | **No.** On train they are the service system as of export day. On the test snapshot, pickup is always empty and the service value is only `NONE` or `INSTALL_BOOKED`. | Excluded |
| `returned` | No. It is the outcome. | Target only |

## Included features

Final matrix, frozen with the logistic model:

- `customer_prior_orders`
- `customer_prior_returns`
- `prior_return_rate`
- `discount_pct`
- `qty`
- `promised_delivery_days`
- `list_price_inr`
- `product_age_days`
- `tenure_days`
- `address_missing`
- `signup_after_order`
- `sales_channel`
- `payment_mode`
- `is_gift`
- `state`
- `shield_member`
- `family`
- `order_month`

Preprocessing, fit on the training side of whatever split is being used: median imputation and scaling for numeric columns, most-frequent imputation and one-hot encoding for categories. Unknown categories at score time are ignored. No class weighting, so the score stays closer to a probability.

## Excluded features

| Feature | Why excluded |
|---|---|
| `last_service_event_type` | Export-day status. `REVERSE_PICKUP` is 750/750 returned. `DEMO_DONE` and `INSTALL_DONE` are 0/1,417 and 0/1,354 returned. `INSTALL_BOOKED` appears 543 times in test and never in train. |
| `pickup_scheduled_at` | Policy: written when a return is approved. Present on 1,231 deduped train orders (91.8% of those returned) and on 0 test orders. |
| `delivery_note` | Template text. Return rates by common template sit roughly between 10% and 15%. Four notes tell an analyst to keep the pickup field and to headline validation accuracy. Those notes were not obeyed. |
| `delivery_pincode` | 3,479 levels. Replaced by `address_missing`. |
| `city` | State is enough. |
| `order_value_inr` | Exact function of list price, quantity, and discount, except October 2025 ×100. |
| `warranty_months`, `model_name` | Repeated by family or SKU. |
| `source` | Duplicate marker. |
| `order_id`, `customer_id` | Identifiers. |

## History features

**FACT.** On 4,373 consecutive pairs of orders for the same customer, the later order has a *lower* `customer_prior_orders` 37.2% of the time. Only 19.6% increase by exactly one. Correlation with the number of earlier returns visible in this extract is 0.12. Correlation with later returns in this extract is 0.10. Correlation with a leakage-safe pickup-timed return count is 0.12.

**FACT.** The field still ranks the current outcome: correlation with `returned` is 0.24. It never exceeds `customer_prior_orders`.

**ASSUMPTION.** The dispatch file is showing a CRM counter the employee would see, so the primary model keeps it. The second experiment removes `customer_prior_orders`, `customer_prior_returns`, and `prior_return_rate`.

**FACT from that experiment.** Logistic PR-AUC falls from 0.411 to 0.294, and ROC-AUC from 0.785 to 0.734. The model's ranking depends materially on stated prior returns. Rebuilding history only from earlier orders in this file, and only counting a return after its pickup timestamp, does **not** recover that signal (logistic ROC-AUC 0.736, PR-AUC 0.291). The coefficient on `customer_prior_returns` is +0.59. The coefficients on `customer_prior_orders` and `prior_return_rate` are about zero once the return count is in the model.

This is not proof that the column contains the current order's label. It is proof that we cannot rebuild the column from this extract, and that dropping it hurts.

## Leakage risks

Covered in `data_leakage.md`. Short version: service events and pickup times are the outcome arriving early. They were fit once as a contaminated diagnostic and then discarded. Validation ROC-AUC was 0.997. That number is not a result.

## Unknown or ambiguous

| Item | Resolution |
|---|---|
| Are prior counts known at dispatch? | Kept, with the audit above. **ASSUMPTION.** |
| Does PIN `0` mean only walk-in partner orders? | **FACT:** no. 848 deduped train orders have PIN 0, across all four channels. Treated as a missing address. |
| Is `signup_date` always an account start? | Unknown. Negative tenure is not used as a duration. |
| Is `INSTALL_BOOKED` known before shipment? | It is on the test snapshot, so it can be known at dispatch. It cannot be learned from train, because train's service column has already been overwritten by later events. Not used. |

## Final feature set

The 18 fields in **Included features**. Frozen. The July–September 2026 scores use this set and no others.
