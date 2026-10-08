# Returns Risk — Recommendation

To: Ritu Deshpande, Head of D2C Operations

## Decision

Pilot this as a pre-dispatch review list. Orders with a predicted return risk of 10% or more go to a confirmation call. Orders at 30% or more are high risk and can be considered for a hold, using the existing hold rule. Shield customers get the same risk score, but the action stays a confirmation call. Do not put a Shield order on a 24-hour hold just because the score is high.

The 95% accuracy figure is not what this pilot delivers. A score that looked that accurate was using information that only exists after a return has already started. It was rejected.

## The number

On the most recent labeled quarter (April–June 2026), checked the way a future month would be checked:

- 89.51% of orders were classified correctly at a conventional cutoff.
- Ranking quality was 0.785 ROC-AUC and 0.411 PR-AUC.
- Calling every order "not a return" would already be 88.48% correct and would catch nothing.

So the model is only a little more accurate than "assume no return," and it is well short of 95%. Its value is the ranked list, not the accuracy percentage. We do not yet know the hit rate on July–September orders. Those outcomes were not in the file.

## The rupees

Policy cost of a completed confirmation call: Rs 45. Policy operating cost of a return, on top of the refund: Rs 1,150. The spring pilot prevented about 35% of returns on the orders that were called.

Using those rates on April–June 2026, calling the orders scored at 10% or above has an estimated net of Rs 37,208 against doing nothing. That is an estimate from historical orders that were not actually called. It is not money already saved. Calling every order is only barely better than calling none, which is why the list matters.

A hold that lasts more than 24 hours is cancelled by the customer about 12% of the time. The policy does not price that cancellation, so this note does not invent one.

## What to do next week

1. Run the call list for one week on non-urgent dispatch, at the 10% line, and record which calls were completed.
2. Keep Shield orders on the call script. Do not hold them overnight.
3. Send the 30% band to a person before any hold, and note whether the customer cancels.
4. Ask the service desk to confirm what "prior returns" on the dispatch screen actually counts. The model relies on it, and the export does not let us rebuild that number.
5. Do not quote 95% to the board from this pilot. Quote the call results after the week.
