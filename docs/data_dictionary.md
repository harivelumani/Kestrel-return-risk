# Data dictionary

Labels used below:

- **FACT** — observed in the task pack or the operations policy.
- **ASSUMPTION** — a choice made because the brief did not settle it.
- **Treatment** — what the model does with the column.

The order tables are `Document/train.csv` and `Document/test_unlabelled.csv`. Reference tables are `customers.csv` and `products.csv`. After dropping exact `partner_feed` copies, train has 10,504 orders. Test has 2,096 orders.

## Orders

| Column | Meaning | Type | Example | Before dispatch? | Safe to use? | Leakage | Treatment |
|---|---|---|---|---|---|---|---|
| `order_id` | Order number | string | `KO2600000` | Yes | Key only | None | Submission key. Not a feature. |
| `order_placed_at` | Placement time, displayed in IST | datetime | `2025-04-01 00:22` | Yes | Yes | None for calendar fields | Time split. `order_month` is a feature. |
| `customer_id` | Key into `customers.csv` | string | `KC100005` | Yes | Key only | Identity memorisation if used raw | Join only. |
| `sku` | Key into `products.csv` | string | `KH-RV-02` | Yes | Via product attributes | None | Join to family and list price. |
| `sales_channel` | `app`, `web`, `marketplace`, `partner_outlet` | category | `app` | Yes | Yes | None | Feature. |
| `payment_mode` | `prepaid_upi`, `prepaid_card`, `cod`, `emi` | category | `cod` | Yes | Yes | None | Feature. COD returns more often (see below). |
| `discount_pct` | Discount at checkout | integer | `8` | Yes | Yes | None | Feature. |
| `qty` | Units | integer | `1` or `2` | Yes | Yes | None | Feature. |
| `order_value_inr` | Value stored by the payment system | float | `4750.02` | Yes | Redundant after cleaning | None, but October 2025 is mis-scaled | Not a feature. **FACT:** outside October 2025 it equals `list_price × qty × (1 − discount/100)` exactly. October 2025 is exactly 100 times that. |
| `promised_delivery_days` | Days promised at checkout | integer 1–12 | `5` | Yes | Yes | None | Feature. Longer promises have higher return rates. |
| `delivery_pincode` | Destination PIN. `0` means no address was stored | integer | `440365` | Yes | Only the missing flag | High cardinality | Raw PIN dropped. `address_missing` (PIN = 0) kept. |
| `is_gift` | Gift order, Y/N | category | `N` | Yes | Yes | None | Feature. |
| `customer_prior_orders` | Stated count of this customer's earlier orders | integer | `1` | Intended yes | Yes, with a consistency warning | Not a clean point-in-time total. See `data_leakage.md` | Feature. |
| `customer_prior_returns` | Stated count of this customer's earlier returns | integer | `0` | Intended yes | Yes, with a consistency warning | Same warning. It never exceeds `customer_prior_orders`, so the current label is not simply added in | Feature. This is the history field the model actually uses. |
| `prior_return_rate` | `customer_prior_returns / customer_prior_orders`, or 0 when there are no prior orders | float | `0.0` | Same as the two counts | Yes | Derived only from those two columns | Feature. **ASSUMPTION:** no prior orders means a prior return rate of 0. After controlling for the return count, its coefficient is about zero. |
| `delivery_note` | Free text from the customer or outlet | string | `Leave with security` | The ordinary templates, yes | No | Four train notes are analyst instructions, not delivery directions | Dropped from the model. Not followed as instructions. |
| `last_service_event_type` | Latest service-system event as of export day | category | `REVERSE_PICKUP` | No on the train extract | No | Post-shipment. Train values include the return itself | Excluded. |
| `pickup_scheduled_at` | Reverse-pickup time | datetime | null on every test row | No | No | Written when a return is approved | Excluded. |
| `source` | `crm` or re-imported `partner_feed` | category | `crm` | Export artifact | No | Duplicate rows, not a second order | Used only to keep the CRM copy. |
| `returned` | 1 if the order was returned. Train only | integer | `0` | No | Target | The label | Not a feature. |

## Customers

| Column | Meaning | Type | Example | Before dispatch? | Safe? | Treatment |
|---|---|---|---|---|---|---|
| `customer_id` | Primary key, 9,000 unique | string | `KC100005` | Yes | Key | Join. 0 unmatched orders. |
| `city` | 18 cities | category | — | Yes | Optional | Dropped. State is the geography feature. |
| `state` | 8 states | category | `MH` | Yes | Yes | Feature. |
| `signup_date` | Signup date | date | `2022-10-15` | Usually | Partly | `tenure_days` when signup is on or before the order. Otherwise missing, with `signup_after_order = 1`. **FACT:** 1,999 labeled orders have a signup after the order, in both Shield and non-Shield. |
| `shield_member` | Kestrel Shield, Y/N | category | `Y` | Yes | Yes | Feature. Shield is scored, not removed. |

## Products

| Column | Meaning | Type | Example | Before dispatch? | Safe? | Treatment |
|---|---|---|---|---|---|---|
| `sku` | Primary key, 21 unique, all present in train and test | string | `KH-RV-02` | Yes | Key | Join. 0 unmatched orders. |
| `family` | Seven appliance families | category | `Robot Vacuum` | Yes | Yes | Feature. |
| `model_name` | Marketing name | string | `Kestrel Robot Vacuum Pro` | Yes | No | Dropped. Same information as SKU. |
| `list_price_inr` | List price | integer | `21999` | Yes | Yes | Feature. |
| `warranty_months` | 12, or 24 for ceiling fans and mixer grinders | integer | `12` | Yes | No | Dropped. It repeats family. |
| `launch_date` | Product launch date | date | `2024-01-27` | Yes | Yes | `product_age_days` at the order. **FACT:** no order is placed before its product's launch. |

## Descriptive return rates on the 10,504 labeled orders

These are descriptions of the labeled history, not validation scores.

| Slice | Orders | Return rate |
|---|---:|---:|
| All deduped orders | 10,504 | 11.42% |
| COD | 3,152 | 18.81% |
| Prepaid UPI | 3,921 | 7.68% |
| Shield | 2,327 | 18.61% |
| Not Shield | 8,177 | 9.38% |
| COD and Shield | 716 | 30.45% |
| Robot vacuum | 1,554 | 19.50% |
| Ceiling fan | 1,531 | 6.66% |
| Gift | 726 | 16.53% |
| Not a gift | 9,778 | 11.05% |

`customer_prior_returns` on the same 10,504 orders: 9.06% returned when the count is 0 (9,119 orders), 19.94% when it is 1 (1,038), 40.81% when it is 2 (223), 53.66% when it is 3 (82). Counts of 4 or more are 42 orders.
