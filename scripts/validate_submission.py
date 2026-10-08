"""Check predictions.csv against sample_submission.csv. Prints PASS or FAIL."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.config import DATA_DIR, ROOT as PROJECT_ROOT


def validate(predictions_path: Path | None = None, sample_path: Path | None = None) -> list[str]:
    predictions_path = predictions_path or (PROJECT_ROOT / "predictions.csv")
    sample_path = sample_path or (DATA_DIR / "sample_submission.csv")
    errors: list[str] = []
    if not predictions_path.exists():
        return [f"Missing {predictions_path}"]
    if not sample_path.exists():
        return [f"Missing {sample_path}. Place the task pack in {DATA_DIR}."]

    predictions = pd.read_csv(predictions_path)
    sample = pd.read_csv(sample_path)
    if list(predictions.columns) != ["order_id", "score"]:
        errors.append(f"Columns are {list(predictions.columns)}, expected ['order_id', 'score'].")
    if len(predictions) != len(sample):
        errors.append(f"Row count {len(predictions)} != sample {len(sample)}.")
    if predictions["order_id"].duplicated().any():
        errors.append("Duplicate order_id in predictions.")
    if sample["order_id"].duplicated().any():
        errors.append("Duplicate order_id in sample_submission.")
    if list(predictions["order_id"]) != list(sample["order_id"]):
        errors.append("order_id values or order do not match sample_submission.csv.")
    scores = pd.to_numeric(predictions["score"], errors="coerce") if "score" in predictions.columns else None
    if scores is None or scores.isna().any():
        errors.append("score has missing or non-numeric values.")
    else:
        if ((scores < 0) | (scores > 1)).any():
            errors.append("score is outside [0, 1].")
        if scores.nunique(dropna=True) <= 1:
            errors.append("score does not vary. Higher score must mean higher return risk.")
        if len(scores) == len(sample["score"]) and scores.round(6).eq(sample["score"].round(6)).all():
            errors.append("predictions.csv is identical to the placeholder sample scores.")
    return errors


def main() -> None:
    errors = validate()
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
