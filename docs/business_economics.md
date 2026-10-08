# Business economics

The model ranks return risk. The priced action is a confirmation call, not a 24-hour hold.

## Policy facts

From Operations Policy v4.1 and the email thread:

- **FACT.** A returned order costs Rs 1,150 on average for reverse pickup, QC, repacking, and write-down, on top of the refund. Farhan says this is the figure he reports. Ritu's "about Rs 600" is not the policy figure. The refund itself is not added on top of the Rs 1,150 in this analysis, and no product margin is available.
- **FACT.** A completed pre-dispatch confirmation call costs Rs 45.
- **FACT.** The spring call pilot prevented about 35% of the returns that would otherwise have happened on called orders.
- **FACT.** An order held more than 24 hours is cancelled by the customer about 12% of the time. No rupee cost of that cancellation is stated. The policy does not say a hold prevents the return on orders that are not cancelled.
- **FACT.** A service contact costs Rs 260 and a technician visit Rs 540. Those are not the dispatch decision, so they are not in the arithmetic below.
- **FACT.** Shield members get free returns within 30 days. They are about a fifth of orders. In this extract they are 22.2% of orders (2,327 / 10,504) and return at 18.6%. No lifetime-value amount is stated. No cost of holding a Shield order is invented.

## Break-even for a call

**ESTIMATE**, using only the two policy rates:

`net = 0.35 × 1,150 × p − 45`

A call has a positive expected value when `p` is above `45 / 402.5 = 11.2%`.

The validation return rate is 11.52%. Calling every one of the 2,126 validation orders would cost Rs 95,670 and, at a 35% prevention rate, avoid about Rs 98,612 of return cost. Estimated net versus doing nothing: about **Rs 2,943**. Calling nobody nets zero. So "call everyone" is only barely better than "call nobody" if the pilot rate holds.

## What the validation window says

These rows are the selected logistic model on April–June 2026. Counts are observed. Rupees are **estimates**: every flagged order is assumed to be a completed Rs 45 call, and 35% of the flagged orders that did return are assumed preventable. Those orders were not actually called. This is not a measured saving.

| Threshold | Flagged | Flagged % | Precision | Recall | FP | FN | Accuracy | Call cost (Rs) | Est. cost avoided (Rs) | Est. net (Rs) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.05 | 1,384 | 65.1% | 0.164 | 0.927 | 1,157 | 18 | 0.447 | 62,280 | 91,368 | 29,088 |
| 0.08 | 1,007 | 47.4% | 0.199 | 0.816 | 807 | 45 | 0.599 | 45,315 | 80,500 | 35,185 |
| **0.10** | **810** | **38.1%** | **0.226** | **0.747** | **627** | **62** | **0.676** | **36,450** | **73,658** | **37,208** |
| 0.11 | 738 | 34.7% | 0.233 | 0.702 | 566 | 73 | 0.699 | 33,210 | 69,230 | 36,020 |
| 0.12 | 671 | 31.6% | 0.244 | 0.669 | 507 | 81 | 0.723 | 30,195 | 66,010 | 35,815 |
| 0.15 | 538 | 25.3% | 0.283 | 0.620 | 386 | 93 | 0.775 | 24,210 | 61,180 | 36,970 |
| 0.20 | 368 | 17.3% | 0.340 | 0.510 | 243 | 120 | 0.829 | 16,560 | 50,313 | 33,753 |
| 0.25 | 269 | 12.7% | 0.379 | 0.416 | 167 | 143 | 0.854 | 12,105 | 41,055 | 28,950 |
| 0.30 | 197 | 9.3% | 0.426 | 0.343 | 113 | 161 | 0.871 | 8,865 | 33,810 | 24,945 |
| 0.50 | 68 | 3.2% | 0.662 | 0.184 | 23 | 200 | 0.895 | 3,060 | 18,112 | 15,052 |

Avoided cost is `true positives × 0.35 × 1,150`. At 0.10 that is `183 × 402.5 = 73,657.5`, and net is **Rs 37,207.50**. Figures in the table are rounded to the nearest rupee.

**ESTIMATE.** On this grid, 0.10 has the highest estimated net. 0.15 is within about Rs 240 of it and flags 272 fewer orders. 0.11, the rough break-even probability, is about Rs 1,200 lower. The peak is flat. It would move if the true prevention rate is not 35%. At a 25% prevention rate, 0.15 beats 0.10. The policy states 35%, so the frozen call threshold is **0.10**.

Accuracy at 0.10 is 67.6%, which is worse than the 88.48% majority baseline, because the call list is large on purpose. Accuracy at 0.50 is 89.51%. Neither is 95%. The 0.50 cutoff leaves 200 of 245 returns uncalled.

## Decision bands

Frozen from the table above. Not refit on July–September 2026.

| Score | Level | Action |
|---|---|---|
| Below 0.10 | Low | Normal dispatch |
| 0.10 up to but not including 0.30 | Review | Confirmation call |
| 0.30 or higher | High | Consider a hold or manual review, **and** still make the call. The hold has no policy price. |

**Why 0.30 for the high band.** It is the first grid point where precision on the validation window is above 40% (42.6%, 84 of 197 flagged orders). That is an operations filter so a person is not asked to review a third of all orders. It is not a claim that a hold is profitable.

**Shield.** Same score, same reasons. The recommended action stays "confirmation call" even above 0.30. Meenal's objection to holding Shield orders is the reason. Ritu still wants those orders scored. No separate Shield tariff is invented.

## What this does not say

- It does not say Kestrel saved Rs 37,208. That is the validation estimate under the pilot rate.
- It does not price a cancelled order. The 12% hold-cancel rate is real, and the rupee cost is unknown.
- It does not apply the estimate to July–September 2026. Those orders have no outcomes in this pack.
