"""Tests for leakage-safe features, the labeled split, and the submission file."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import DATA_DIR
from src.features import LEAKY_COLUMNS, add_point_in_time_history, feature_columns
from scripts.validate_submission import validate


class PointInTimeHistoryTests(unittest.TestCase):
    def test_future_pickup_is_not_counted_yet(self) -> None:
        frame = pd.DataFrame(
            {
                "customer_id": ["A", "A", "A"],
                "order_placed_at": pd.to_datetime(["2026-01-01", "2026-01-10", "2026-03-01"]),
                "returned": [1, 0, 0],
                "pickup_at": pd.to_datetime(["2026-01-20", pd.NaT, pd.NaT]),
            }
        )
        scored = add_point_in_time_history(frame)
        self.assertEqual(scored.loc[0, "pit_prior_orders"], 0)
        self.assertEqual(scored.loc[0, "pit_prior_returns"], 0)
        # The January 20 pickup is still in the future on January 10.
        self.assertEqual(scored.loc[1, "pit_prior_orders"], 1)
        self.assertEqual(scored.loc[1, "pit_prior_returns"], 0)
        self.assertEqual(scored.loc[2, "pit_prior_orders"], 2)
        self.assertEqual(scored.loc[2, "pit_prior_returns"], 1)

    def test_current_label_is_not_part_of_history(self) -> None:
        frame = pd.DataFrame(
            {
                "customer_id": ["B"],
                "order_placed_at": pd.to_datetime(["2026-05-01"]),
                "returned": [1],
                "pickup_at": pd.to_datetime(["2026-05-20"]),
            }
        )
        scored = add_point_in_time_history(frame)
        self.assertEqual(scored.loc[0, "pit_prior_returns"], 0)


class FeaturePolicyTests(unittest.TestCase):
    def test_primary_matrix_excludes_post_shipment_fields(self) -> None:
        columns = set(feature_columns(True))
        self.assertTrue(columns.isdisjoint(LEAKY_COLUMNS))
        self.assertIn("customer_prior_returns", columns)
        self.assertIn("shield_member", columns)
        self.assertNotIn("city", columns)


class SubmissionValidationTests(unittest.TestCase):
    def test_placeholder_sample_fails_closed(self) -> None:
        sample = DATA_DIR / "sample_submission.csv"
        if not sample.exists():
            self.skipTest("Task pack is not in Document/.")
        errors = validate(sample, sample)
        self.assertTrue(errors)

    def test_real_predictions_pass_when_present(self) -> None:
        predictions = ROOT / "predictions.csv"
        sample = DATA_DIR / "sample_submission.csv"
        if not predictions.exists() or not sample.exists():
            self.skipTest("predictions.csv or the task pack is missing.")
        self.assertEqual(validate(predictions, sample), [])

    def test_missing_field_fails(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            sample = Path(folder) / "sample.csv"
            bad = Path(folder) / "bad.csv"
            sample.write_text("order_id,score\nA,0.5\n", encoding="utf-8")
            bad.write_text("order_id\nA\n", encoding="utf-8")
            errors = validate(bad, sample)
            self.assertTrue(any("Columns" in error for error in errors))


class LabeledDataTests(unittest.TestCase):
    def test_dedup_split_and_value_scale(self) -> None:
        if not (DATA_DIR / "train.csv").exists():
            self.skipTest("Task pack is not in Document/.")
        from src.data import load_labeled_orders, split_fit_val

        labeled = load_labeled_orders()
        fit, val = split_fit_val(labeled)
        self.assertEqual(len(labeled), 10504)
        self.assertEqual(int(labeled["returned"].sum()), 1200)
        self.assertEqual(len(fit), 8378)
        self.assertEqual(int(fit["returned"].sum()), 955)
        self.assertEqual(len(val), 2126)
        self.assertEqual(int(val["returned"].sum()), 245)
        self.assertLess(fit["order_placed_at"].max(), val["order_placed_at"].min())
        self.assertEqual(len(labeled), labeled["order_id"].nunique())


if __name__ == "__main__":
    unittest.main()
