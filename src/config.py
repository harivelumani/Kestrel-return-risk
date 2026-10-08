"""Project paths and frozen experiment settings.

Paths are relative to the repository root. Override the task-pack location
with KESTREL_DATA_DIR if the files are not in Document/.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("KESTREL_DATA_DIR", ROOT / "Document"))
ARTIFACT_DIR = ROOT / "artifacts"
REPORT_DIR = ROOT / "reports"

RANDOM_SEED = 42

# Primary temporal split. Validation ends where the unlabeled test period begins.
FIT_END = "2026-04-01"  # fit: order_placed_at < FIT_END
VAL_END = "2026-07-01"  # validation: FIT_END <= order_placed_at < VAL_END

# Policy figures (Rs). Do not invent values beyond these.
RETURN_OPERATING_COST_INR = 1150
CALL_COST_INR = 45
CALL_PREVENTION_RATE = 0.35
HOLD_CANCEL_RATE = 0.12

# A return on an earlier order is treated as known at a later dispatch only
# once its reverse-pickup timestamp is already in the past. This is used only
# for the leakage-safe history diagnostic, not as a model input on the
# current order.
HISTORY_COLUMNS = (
    "customer_prior_orders",
    "customer_prior_returns",
    "prior_return_rate",
)

THRESHOLDS = (0.05, 0.08, 0.10, 0.11, 0.12, 0.15, 0.20, 0.25, 0.30, 0.50)

# Frozen after temporal validation. Do not retune on the unlabeled test file.
# Call threshold maximises estimated net rupees on the Apr–Jun 2026 window
# under the policy prevention rate. 0.10 through 0.15 are a plateau.
# High-risk is an unpriced manual-review band: validation precision first
# exceeds 40% at 0.30. Shield orders are never recommended for a 24-hour hold.
SELECTED_MODEL = "logistic"
SELECTED_HISTORY = "supplied"
CALL_THRESHOLD = 0.10
HIGH_RISK_THRESHOLD = 0.30
