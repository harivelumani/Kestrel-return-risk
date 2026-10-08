"""Fit the temporal-validation experiments and write reports/experiment_results.json.

Does not score the July–September 2026 file and does not refit on all labels.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import RANDOM_SEED, REPORT_DIR, THRESHOLDS
from src.data import load_labeled_orders, split_fit_val
from src.features import add_dispatch_features, add_point_in_time_history, design_matrix
from src.metrics import (
    classification_report,
    majority_scores,
    ranking_report,
    reliability_table,
    threshold_table,
)
from src.modeling import make_pipeline, positive_scores


def _history_audit(labeled: pd.DataFrame) -> dict:
    frame = labeled.sort_values(["customer_id", "order_placed_at", "order_id"]).copy()
    group = frame.groupby("customer_id", sort=False)
    previous = group["customer_prior_orders"].shift(1)
    delta = frame["customer_prior_orders"] - previous
    comparable = delta.dropna()
    multi = frame[frame["customer_id"].duplicated(keep=False)].copy()
    multi["returns_before"] = multi.groupby("customer_id")["returned"].cumsum() - multi["returned"]
    multi["returns_after"] = (
        multi.groupby("customer_id")["returned"].transform("sum") - multi.groupby("customer_id")["returned"].cumsum()
    )
    return {
        "orders": int(len(frame)),
        "consecutive_pairs": int(len(comparable)),
        "share_prior_orders_decrease": float((comparable < 0).mean()),
        "share_prior_orders_increase_by_one": float((comparable == 1).mean()),
        "corr_supplied_returns_vs_current_label": float(
            frame["customer_prior_returns"].corr(frame["returned"])
        ),
        "corr_supplied_returns_vs_pit_returns": float(
            multi["customer_prior_returns"].corr(multi["pit_prior_returns"])
        )
        if len(multi)
        else None,
        "corr_pit_returns_vs_current_label": float(frame["pit_prior_returns"].corr(frame["returned"])),
        "corr_supplied_returns_vs_earlier_extract_returns": float(
            multi["customer_prior_returns"].corr(multi["returns_before"])
        ),
        "corr_supplied_returns_vs_later_extract_returns": float(
            multi["customer_prior_returns"].corr(multi["returns_after"])
        ),
    }


def _fit_score(fit: pd.DataFrame, val: pd.DataFrame, history_source: str, model_name: str) -> dict:
    include_history = history_source != "none"
    y_fit = fit["returned"].to_numpy()
    y_val = val["returned"].to_numpy()
    pipeline = make_pipeline(include_history, model_name)
    x_fit = design_matrix(fit, include_history, history_source)
    x_val = design_matrix(val, include_history, history_source)
    pipeline.fit(x_fit, y_fit)
    scores = positive_scores(pipeline, x_val)
    ranking = ranking_report(y_val, scores)
    at_half = classification_report(y_val, scores, 0.5)
    table = threshold_table(y_val, scores, THRESHOLDS)
    best_net = table.loc[table["estimated_net_inr"].idxmax()]
    result = {
        "model": model_name,
        "history_source": history_source,
        "features": list(x_fit.columns),
        "ranking": ranking,
        "at_0_50": at_half,
        "thresholds": table.to_dict(orient="records"),
        "best_net_threshold": float(best_net["threshold"]),
        "best_estimated_net_inr": float(best_net["estimated_net_inr"]),
    }
    if model_name == "logistic" and history_source == "supplied":
        result["coefficients"] = _top_coefficients(pipeline, 10_000)
        result["reliability"] = reliability_table(y_val, scores)
    return result


def _top_coefficients(pipeline: Pipeline, k: int) -> list[dict]:
    preprocessor: ColumnTransformer = pipeline.named_steps["preprocess"]
    model: LogisticRegression = pipeline.named_steps["model"]
    names = preprocessor.get_feature_names_out()
    coef = model.coef_[0]
    rows = [{"feature": str(name), "coefficient": float(value)} for name, value in zip(names, coef)]
    rows.sort(key=lambda row: row["coefficient"])
    if len(rows) > k:
        rows = rows[: k // 2] + rows[-k // 2 :]
    return rows


def _leaky_diagnostic(fit: pd.DataFrame, val: pd.DataFrame) -> dict:
    """Contaminated model. Not a candidate. Shows why export-day service fields cannot be used."""

    def matrix(frame: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(
            {
                "has_pickup": frame["pickup_at"].notna().astype(int),
                "last_service_event_type": frame["last_service_event_type"].astype(str),
            }
        )
        return out

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), ["has_pickup"]),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                ["last_service_event_type"],
            ),
        ]
    )
    pipeline = Pipeline(
        [
            ("preprocess", preprocessor),
            ("model", LogisticRegression(max_iter=1000, random_state=RANDOM_SEED)),
        ]
    )
    pipeline.fit(matrix(fit), fit["returned"].to_numpy())
    scores = positive_scores(pipeline, matrix(val))
    y_val = val["returned"].to_numpy()
    return {
        "model": "logistic_on_export_day_service_fields",
        "warning": "CONTAMINATED. Export-day service and pickup fields. Not eligible for selection.",
        "ranking": ranking_report(y_val, scores),
        "at_0_50": classification_report(y_val, scores, 0.5),
    }


def _majority(fit: pd.DataFrame, val: pd.DataFrame) -> dict:
    rate = float(fit["returned"].mean())
    y_val = val["returned"].to_numpy()
    scores = majority_scores(len(val), rate)
    hard = np.zeros(len(val), dtype=int)
    table = threshold_table(y_val, scores, THRESHOLDS)
    try:
        roc = float(roc_auc_score(y_val, scores))
    except ValueError:
        roc = 0.5
    return {
        "model": "majority_baseline",
        "history_source": "none",
        "fit_return_rate": rate,
        "hard_negative_accuracy": float((hard == y_val).mean()),
        "ranking": {
            "roc_auc": roc,
            "pr_auc": float(average_precision_score(y_val, scores)),
            "brier": float(brier_score_loss(y_val, scores)),
        },
        "at_0_50": classification_report(y_val, scores, 0.5),
        "thresholds": table.to_dict(orient="records"),
    }


def main() -> None:
    labeled = load_labeled_orders()
    labeled = add_dispatch_features(labeled)
    labeled = add_point_in_time_history(labeled)
    fit, val = split_fit_val(labeled)
    expected = {
        "labeled": (10504, 1200),
        "fit": (8378, 955),
        "val": (2126, 245),
    }
    actual = {
        "labeled": (len(labeled), int(labeled["returned"].sum())),
        "fit": (len(fit), int(fit["returned"].sum())),
        "val": (len(val), int(val["returned"].sum())),
    }
    if actual != expected:
        raise SystemExit(f"Split counts changed. Expected {expected}, got {actual}. Stopping.")

    experiments = [
        _majority(fit, val),
        _fit_score(fit, val, "supplied", "logistic"),
        _fit_score(fit, val, "supplied", "hist_gradient_boosting"),
        _fit_score(fit, val, "none", "logistic"),
        _fit_score(fit, val, "none", "hist_gradient_boosting"),
        _fit_score(fit, val, "pit", "logistic"),
        _fit_score(fit, val, "pit", "hist_gradient_boosting"),
    ]
    payload = {
        "split": actual,
        "history_audit": _history_audit(labeled),
        "experiments": experiments,
        "contaminated_diagnostic": _leaky_diagnostic(fit, val),
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    destination = REPORT_DIR / "experiment_results.json"
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {destination}")
    for experiment in experiments:
        ranking = experiment["ranking"]
        print(
            f"{experiment['model']:28} {experiment.get('history_source', ''):10} "
            f"ROC {ranking['roc_auc']:.4f} PR {ranking['pr_auc']:.4f} "
            f"Brier {ranking['brier']:.4f} "
            f"acc@0.5 {experiment['at_0_50']['accuracy']:.4f} "
            f"rec@0.5 {experiment['at_0_50']['recall']:.4f}"
        )
    leak = payload["contaminated_diagnostic"]["ranking"]
    print(
        f"{'LEAKY diagnostic':28} {'service':10} "
        f"ROC {leak['roc_auc']:.4f} PR {leak['pr_auc']:.4f}"
    )


if __name__ == "__main__":
    main()
