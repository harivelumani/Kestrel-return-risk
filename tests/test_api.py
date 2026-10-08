"""API contract tests. They load the frozen artifact and do not refit it."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import app
from src.features import add_dispatch_features, design_matrix
from src.modeling import positive_scores
from src.service import load_model, record_frame

VALID = {
    "order_placed_at": "2026-08-15T10:00:00",
    "sales_channel": "web",
    "payment_mode": "prepaid_upi",
    "discount_pct": 5,
    "qty": 1,
    "promised_delivery_days": 4,
    "delivery_pincode": 560001,
    "is_gift": "N",
    "customer_prior_orders": 1,
    "customer_prior_returns": 0,
    "signup_date": "2024-06-01",
    "state": "MH",
    "shield_member": "N",
    "family": "Ceiling Fan",
    "list_price_inr": 3499,
    "launch_date": "2024-01-01",
}

HIGH = {
    "order_placed_at": "2026-08-15T10:00:00",
    "sales_channel": "marketplace",
    "payment_mode": "cod",
    "discount_pct": 25,
    "qty": 1,
    "promised_delivery_days": 12,
    "delivery_pincode": 0,
    "is_gift": "Y",
    "customer_prior_orders": 6,
    "customer_prior_returns": 4,
    "signup_date": "2023-01-01",
    "state": "KA",
    "shield_member": "N",
    "family": "Robot Vacuum",
    "list_price_inr": 30000,
    "launch_date": "2023-06-01",
}

SHIELD_HIGH = {**HIGH, "shield_member": "Y"}


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_valid_prediction_schema_and_stability(self):
        first = self.client.post("/predict", json=VALID)
        second = self.client.post("/predict", json=VALID)
        self.assertEqual(first.status_code, 200, first.text)
        body = first.json()
        for key in ("risk_score", "risk_level", "recommended_action", "reasons", "shield_handling"):
            self.assertIn(key, body)
        self.assertIsInstance(body["risk_score"], float)
        self.assertGreaterEqual(body["risk_score"], 0)
        self.assertLessEqual(body["risk_score"], 1)
        self.assertIn(body["risk_level"], {"LOW", "REVIEW", "HIGH"})
        self.assertIsInstance(body["reasons"], list)
        self.assertGreaterEqual(len(body["reasons"]), 1)
        self.assertTrue(all(isinstance(item, str) and item for item in body["reasons"]))
        self.assertIsNone(body["shield_handling"])
        self.assertEqual(first.json(), second.json())

    def test_missing_required_field(self):
        payload = dict(VALID)
        del payload["payment_mode"]
        response = self.client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn("payment_mode", response.json()["detail"])

    def test_invalid_input(self):
        payload = dict(VALID)
        payload["payment_mode"] = "bitcoin"
        response = self.client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn("payment_mode", response.json()["detail"])
        payload = dict(VALID)
        payload["customer_prior_returns"] = 5
        payload["customer_prior_orders"] = 1
        response = self.client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_shield_high_risk_is_a_call_not_a_hold(self):
        response = self.client.post("/predict", json=SHIELD_HIGH)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertGreaterEqual(body["risk_score"], 0.30)
        self.assertEqual(body["risk_level"], "HIGH")
        self.assertEqual(body["recommended_action"], "Confirmation call")
        self.assertIn("not a 24-hour hold", body["shield_handling"])

    def test_high_risk_non_shield_considers_hold(self):
        response = self.client.post("/predict", json=HIGH)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertGreaterEqual(body["risk_score"], 0.30)
        self.assertEqual(body["risk_level"], "HIGH")
        self.assertEqual(body["recommended_action"], "Consider hold")
        self.assertIsNone(body["shield_handling"])

    def test_score_matches_training_pipeline(self):
        artifact = load_model()
        frame = add_dispatch_features(record_frame(VALID))
        matrix = design_matrix(frame, include_history=True, history_source="supplied")
        offline = round(float(positive_scores(artifact["pipeline"], matrix)[0]), 6)
        response = self.client.post("/predict", json=VALID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["risk_score"], offline)


if __name__ == "__main__":
    unittest.main()
