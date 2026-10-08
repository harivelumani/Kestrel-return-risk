"""Score one dispatch record with the frozen logistic pipeline.

The API and the offline scorer both call `score_record`. Feature construction
is `add_dispatch_features` plus `design_matrix`, the same functions used
when the model was trained.
"""

from __future__ import annotations

from functools import lru_cache

import joblib
import pandas as pd

from src.config import ARTIFACT_DIR, CALL_THRESHOLD, HIGH_RISK_THRESHOLD
from src.features import add_dispatch_features, design_matrix
from src.modeling import positive_scores

MONTHS = {
    "01": "January",
    "02": "February",
    "03": "March",
    "04": "April",
    "05": "May",
    "06": "June",
    "07": "July",
    "08": "August",
    "09": "September",
    "10": "October",
    "11": "November",
    "12": "December",
}
STATES = {
    "MH": "Maharashtra",
    "KA": "Karnataka",
    "RJ": "Rajasthan",
    "MP": "Madhya Pradesh",
    "TS": "Telangana",
    "TN": "Tamil Nadu",
    "DL": "Delhi",
    "UP": "Uttar Pradesh",
}

# Employee-facing lines. A line is used only when that feature's contribution
# has the stated sign on this order.
HIGHER = {
    "num__customer_prior_returns": "This customer has a relatively high number of returns on previous orders.",
    "num__customer_prior_orders": "This customer has placed relatively many previous orders.",
    "num__prior_return_rate": "A relatively high share of this customer's previous orders were returned.",
    "num__discount_pct": "The checkout discount is relatively high.",
    "num__qty": "The order quantity is relatively high.",
    "num__promised_delivery_days": "The promised delivery window is relatively long.",
    "num__list_price_inr": "The product list price is relatively high.",
    "num__product_age_days": "This product has been on sale for a relatively long time.",
    "num__tenure_days": "This customer has been signed up for a relatively long time.",
    "num__address_missing": "No delivery address was captured for this order.",
    "num__signup_after_order": "The customer signup date is after this order date.",
    "cat__payment_mode_cod": "The order is cash on delivery, which has a higher historical return rate.",
    "cat__payment_mode_emi": "The order is on EMI.",
    "cat__payment_mode_prepaid_upi": "The payment mode on this order is prepaid UPI.",
    "cat__payment_mode_prepaid_card": "The payment mode on this order is a prepaid card.",
    "cat__shield_member_Y": "This customer is a Shield member. Shield orders have a higher historical return rate.",
    "cat__shield_member_N": "This customer is not a Shield member.",
    "cat__is_gift_Y": "This order is marked as a gift.",
    "cat__is_gift_N": "This order is not marked as a gift.",
    "cat__sales_channel_marketplace": "The order came through the marketplace, which has a higher historical return rate.",
    "cat__sales_channel_app": "The order was placed in the app.",
    "cat__sales_channel_web": "The order was placed on the web.",
    "cat__sales_channel_partner_outlet": "The order came from a partner outlet.",
    "cat__family_Robot Vacuum": "Robot vacuums have a higher historical return rate than other families.",
    "cat__family_Water Purifier": "Water purifiers have a higher historical return rate than several other families.",
    "cat__family_Air Fryer": "Air fryers contribute to a higher predicted return risk on this order.",
    "cat__family_Room Heater": "Room heaters contribute to a higher predicted return risk on this order.",
    "cat__family_Ceiling Fan": "The product family is ceiling fans.",
    "cat__family_Mixer Grinder": "The product family is mixer grinders.",
    "cat__family_Induction Cooktop": "The product family is induction cooktops.",
}
LOWER = {
    "num__customer_prior_returns": "This customer has few or no returns on previous orders.",
    "num__customer_prior_orders": "This customer has relatively few previous orders.",
    "num__prior_return_rate": "Previous orders from this customer have a low return rate.",
    "num__discount_pct": "The checkout discount is relatively low.",
    "num__qty": "The order quantity is a single unit.",
    "num__promised_delivery_days": "The promised delivery window is relatively short.",
    "num__list_price_inr": "The product list price is relatively low.",
    "num__product_age_days": "This is a relatively newer product.",
    "num__tenure_days": "This customer signed up relatively recently.",
    "num__address_missing": "A delivery address was captured for this order.",
    "num__signup_after_order": "The customer was already signed up when the order was placed.",
    "cat__payment_mode_prepaid_upi": "Prepaid UPI payments have a lower historical return rate.",
    "cat__payment_mode_prepaid_card": "Prepaid card payments have a lower historical return rate.",
    "cat__payment_mode_emi": "EMI payments have a lower historical return rate than cash on delivery.",
    "cat__payment_mode_cod": "Cash on delivery is not the payment mode on this order.",
    "cat__shield_member_N": "This customer is not a Shield member. Non-Shield orders have a lower historical return rate.",
    "cat__shield_member_Y": "Shield membership is not pushing this score down.",
    "cat__is_gift_N": "This is not a gift order.",
    "cat__is_gift_Y": "The gift flag is not increasing predicted risk on this order.",
    "cat__sales_channel_partner_outlet": "Partner-outlet orders have a lower historical return rate.",
    "cat__sales_channel_app": "The app channel is associated with lower predicted risk on this order.",
    "cat__sales_channel_web": "The web channel is associated with lower predicted risk on this order.",
    "cat__sales_channel_marketplace": "The marketplace channel is not increasing predicted risk on this order.",
    "cat__family_Ceiling Fan": "Ceiling fans have a lower historical return rate.",
    "cat__family_Mixer Grinder": "Mixer grinders have a lower historical return rate.",
    "cat__family_Induction Cooktop": "Induction cooktops have a lower historical return rate.",
    "cat__family_Robot Vacuum": "The product family is not increasing predicted risk on this order.",
    "cat__family_Water Purifier": "The product family is not increasing predicted risk on this order.",
    "cat__family_Air Fryer": "The product family is not increasing predicted risk on this order.",
    "cat__family_Room Heater": "The product family is not increasing predicted risk on this order.",
}


class ModelNotAvailable(FileNotFoundError):
    """Raised when artifacts/model.joblib is missing."""


def load_model(path=None):
    artifact_path = path or (ARTIFACT_DIR / "model.joblib")
    if not artifact_path.exists():
        raise ModelNotAvailable(
            "The trained model file is missing. From the project folder run: python scripts/fit_final.py"
        )
    artifact = joblib.load(artifact_path)
    if "pipeline" not in artifact:
        raise ModelNotAvailable("The model file does not contain the training pipeline.")
    return artifact


@lru_cache(maxsize=1)
def cached_model():
    return load_model()


def record_frame(payload: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "order_placed_at": pd.Timestamp(payload["order_placed_at"]),
                "launch_date": pd.Timestamp(payload["launch_date"]),
                "signup_date": pd.Timestamp(payload["signup_date"]),
                "delivery_pincode": int(payload["delivery_pincode"]),
                "customer_prior_orders": int(payload["customer_prior_orders"]),
                "customer_prior_returns": int(payload["customer_prior_returns"]),
                "discount_pct": float(payload["discount_pct"]),
                "qty": int(payload["qty"]),
                "promised_delivery_days": int(payload["promised_delivery_days"]),
                "list_price_inr": float(payload["list_price_inr"]),
                "sales_channel": payload["sales_channel"],
                "payment_mode": payload["payment_mode"],
                "is_gift": payload["is_gift"],
                "state": payload["state"],
                "shield_member": payload["shield_member"],
                "family": payload["family"],
            }
        ]
    )


def _phrase(feature_name: str, contribution: float) -> str | None:
    if feature_name.startswith("cat__order_month_"):
        month = MONTHS.get(feature_name.rsplit("_", 1)[-1], "")
        if not month:
            return None
        if contribution > 0:
            return f"Orders placed in {month} have historically been associated with higher return risk."
        return f"Orders placed in {month} have historically been associated with lower return risk."
    if feature_name.startswith("cat__state_"):
        code = feature_name.rsplit("_", 1)[-1]
        state = STATES.get(code, code)
        if contribution > 0:
            return f"Orders delivered in {state} have a somewhat higher historical return rate."
        return f"Orders delivered in {state} have a somewhat lower historical return rate."
    table = HIGHER if contribution > 0 else LOWER
    return table.get(feature_name)


def explain(pipeline, matrix, level: str) -> list[str]:
    """Top feature contributions for this row. No text is emitted for a zero contribution."""
    transformed = pipeline.named_steps["preprocess"].transform(matrix)
    names = list(pipeline.named_steps["preprocess"].get_feature_names_out())
    coefficients = pipeline.named_steps["model"].coef_[0]
    contributions = list(zip(names, transformed[0] * coefficients))
    if level == "LOW":
        ranked = sorted(contributions, key=lambda item: item[1])
        useful = [(name, value) for name, value in ranked if value < -0.02]
    else:
        ranked = sorted(contributions, key=lambda item: item[1], reverse=True)
        useful = [(name, value) for name, value in ranked if value > 0.02]
    reasons: list[str] = []
    for name, value in useful:
        text = _phrase(str(name), float(value))
        if text and text not in reasons:
            reasons.append(text)
        if len(reasons) == 3:
            break
    if reasons:
        return reasons
    name, value = max(contributions, key=lambda item: abs(item[1]))
    text = _phrase(str(name), float(value))
    return [text] if text else []


def decide(score: float, shield_member: str) -> dict:
    if score >= HIGH_RISK_THRESHOLD:
        level = "HIGH"
        action = "Confirmation call" if shield_member == "Y" else "Consider hold"
    elif score >= CALL_THRESHOLD:
        level = "REVIEW"
        action = "Confirmation call"
    else:
        level = "LOW"
        action = "Normal dispatch"
    shield_handling = None
    if shield_member == "Y":
        shield_handling = (
            "Shield member: the risk score is unchanged. "
            "Recommend a confirmation call, not a 24-hour hold."
        )
    return {
        "risk_level": level,
        "recommended_action": action,
        "shield_handling": shield_handling,
    }


def score_record(payload: dict, artifact=None) -> dict:
    artifact = artifact or cached_model()
    frame = add_dispatch_features(record_frame(payload))
    matrix = design_matrix(frame, include_history=True, history_source="supplied")
    pipeline = artifact["pipeline"]
    score = round(float(positive_scores(pipeline, matrix)[0]), 6)
    decision = decide(score, payload["shield_member"])
    return {
        "risk_score": score,
        "risk_level": decision["risk_level"],
        "recommended_action": decision["recommended_action"],
        "reasons": explain(pipeline, matrix, decision["risk_level"]),
        "shield_handling": decision["shield_handling"],
    }
