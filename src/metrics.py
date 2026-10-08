"""Validation metrics and policy-based call economics.

Rupee figures that depend on the 35% pilot prevention rate are estimates.
The Rs 45 and Rs 1,150 inputs are policy facts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.config import CALL_COST_INR, CALL_PREVENTION_RATE, RETURN_OPERATING_COST_INR


def classification_report(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    predicted = (scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    flagged = int(tp + fp)
    n = int(len(y_true))
    intervention = flagged * CALL_COST_INR
    # ESTIMATE: each true would-be return that is called is prevented with
    # the pilot rate. Historical labels were observed without that call.
    avoided = tp * CALL_PREVENTION_RATE * RETURN_OPERATING_COST_INR
    return {
        "threshold": threshold,
        "n": n,
        "accuracy": float(accuracy_score(y_true, predicted)),
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "flagged": flagged,
        "flagged_pct": flagged / n if n else 0.0,
        "intervention_cost_inr": float(intervention),
        "estimated_return_cost_avoided_inr": float(avoided),
        "estimated_net_inr": float(avoided - intervention),
    }


def ranking_report(y_true: np.ndarray, scores: np.ndarray) -> dict:
    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    return {
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "pr_auc": float(average_precision_score(y_true, scores)),
        "brier": float(brier_score_loss(y_true, scores)),
    }


def threshold_table(y_true: np.ndarray, scores: np.ndarray, thresholds: tuple[float, ...]) -> pd.DataFrame:
    rows = [classification_report(y_true, scores, threshold) for threshold in thresholds]
    return pd.DataFrame(rows)


def reliability_table(y_true: np.ndarray, scores: np.ndarray, bins: int = 8) -> list[dict]:
    frame = pd.DataFrame({"y": np.asarray(y_true).astype(int), "p": np.asarray(scores, dtype=float)})
    frame["bin"] = pd.qcut(frame["p"], bins, duplicates="drop")
    rows = []
    for interval, group in frame.groupby("bin", observed=True):
        rows.append(
            {
                "bin": str(interval),
                "n": int(len(group)),
                "mean_score": float(group["p"].mean()),
                "observed_return_rate": float(group["y"].mean()),
            }
        )
    return rows


def majority_scores(n: int, positive_rate: float) -> np.ndarray:
    """Constant score equal to the training return rate.

    Hard labels at any threshold above that rate flag nobody. Accuracy of
    the all-negative classifier is reported separately.
    """
    return np.full(n, positive_rate, dtype=float)
