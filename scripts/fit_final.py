"""Refit the selected model on every labeled order and score the test window.

The model and threshold are frozen from the temporal validation run.
This script does not retune them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import joblib

from src.config import (
    ARTIFACT_DIR,
    CALL_THRESHOLD,
    DATA_DIR,
    HIGH_RISK_THRESHOLD,
    ROOT as PROJECT_ROOT,
    SELECTED_HISTORY,
    SELECTED_MODEL,
)
from src.data import load_labeled_orders, load_test_orders
from src.features import add_dispatch_features, design_matrix, feature_columns
from src.modeling import make_pipeline, positive_scores


def main() -> None:
    if SELECTED_HISTORY != "supplied" or SELECTED_MODEL != "logistic":
        raise SystemExit(
            "fit_final.py is wired to the frozen logistic model with supplied history. "
            "Update it deliberately if the selection changes."
        )
    labeled = add_dispatch_features(load_labeled_orders())
    test = add_dispatch_features(load_test_orders())
    include_history = True
    pipeline = make_pipeline(include_history, SELECTED_MODEL)
    x_train = design_matrix(labeled, include_history, "supplied")
    pipeline.fit(x_train, labeled["returned"].to_numpy())

    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    x_test = design_matrix(test, include_history, "supplied")
    scored = test[["order_id"]].copy()
    scored["score"] = positive_scores(pipeline, x_test)
    merged = sample[["order_id"]].merge(scored, on="order_id", how="left", validate="one_to_one")
    if merged["score"].isna().any():
        raise SystemExit("Some sample order ids did not receive a score.")
    if len(merged) != len(sample):
        raise SystemExit("Prediction row count does not match sample_submission.csv.")
    merged["score"] = merged["score"].round(6)
    destination = PROJECT_ROOT / "predictions.csv"
    merged.to_csv(destination, index=False)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    artifact = {
        "pipeline": pipeline,
        "model_name": SELECTED_MODEL,
        "history_source": SELECTED_HISTORY,
        "feature_columns": feature_columns(True),
        "call_threshold": CALL_THRESHOLD,
        "high_risk_threshold": HIGH_RISK_THRESHOLD,
        "trained_on_orders": int(len(labeled)),
        "positive_rate": float(labeled["returned"].mean()),
    }
    joblib.dump(artifact, ARTIFACT_DIR / "model.joblib")
    summary = {
        "predictions": str(destination),
        "rows": int(len(merged)),
        "score_min": float(merged["score"].min()),
        "score_max": float(merged["score"].max()),
        "score_mean": float(merged["score"].mean()),
        "share_at_or_above_call_threshold": float((merged["score"] >= CALL_THRESHOLD).mean()),
        "share_at_or_above_high_threshold": float((merged["score"] >= HIGH_RISK_THRESHOLD).mean()),
        "duplicate_order_ids": int(merged["order_id"].duplicated().sum()),
    }
    print(json.dumps(summary, indent=2))
    if not np.isfinite(merged["score"]).all():
        raise SystemExit("Non-finite scores.")


if __name__ == "__main__":
    main()
