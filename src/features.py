"""Row-level features that are known before dispatch.

Supplied prior-order counts are copied from the dispatch snapshot.
Point-in-time counts are a separate diagnostic built only from earlier
orders, and only from returns whose reverse pickup was already timestamped
before the order being scored.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import HISTORY_COLUMNS

CATEGORICAL_FEATURES = (
    "sales_channel",
    "payment_mode",
    "is_gift",
    "state",
    "shield_member",
    "family",
    "order_month",
)

NUMERIC_BASE = (
    "discount_pct",
    "qty",
    "promised_delivery_days",
    "list_price_inr",
    "product_age_days",
    "tenure_days",
    "address_missing",
    "signup_after_order",
)

LEAKY_COLUMNS = (
    "last_service_event_type",
    "pickup_scheduled_at",
    "pickup_at",
    "returned",
    "source",
    "delivery_note",
    "delivery_pincode",
    "city",
    "order_value_inr",
)


def feature_columns(include_history: bool) -> list[str]:
    columns = list(NUMERIC_BASE) + list(CATEGORICAL_FEATURES)
    if include_history:
        columns = list(HISTORY_COLUMNS) + columns
    return columns


def add_dispatch_features(orders: pd.DataFrame) -> pd.DataFrame:
    """Features computed from the current row only. No cross-order aggregates."""
    frame = orders.copy()
    frame["order_month"] = frame["order_placed_at"].dt.strftime("%m")
    frame["product_age_days"] = (
        frame["order_placed_at"].dt.normalize() - frame["launch_date"]
    ).dt.days
    tenure = (frame["order_placed_at"].dt.normalize() - frame["signup_date"]).dt.days
    frame["signup_after_order"] = (tenure < 0).astype(int)
    frame["tenure_days"] = tenure.where(tenure >= 0)
    frame["address_missing"] = (frame["delivery_pincode"] == 0).astype(int)
    prior_orders = frame["customer_prior_orders"].astype(float)
    prior_returns = frame["customer_prior_returns"].astype(float)
    if (prior_returns > prior_orders).any():
        raise ValueError("customer_prior_returns exceeds customer_prior_orders.")
    frame["prior_return_rate"] = np.where(prior_orders > 0, prior_returns / prior_orders, 0.0)
    if (frame["product_age_days"] < 0).any():
        raise ValueError("A product launch date is after the order timestamp.")
    return frame


def add_point_in_time_history(orders: pd.DataFrame) -> pd.DataFrame:
    """Count earlier orders, and earlier returns only if pickup was already booked.

    `returned` on the current row is never read. A later order cannot
    contribute. Test rows have no pickup and no label, so they can add to a
    subsequent order count but never to a return count.
    """
    frame = orders.copy()
    prior_orders = np.zeros(len(frame), dtype=float)
    prior_returns = np.zeros(len(frame), dtype=float)
    work = pd.DataFrame(
        {
            "customer_id": frame["customer_id"].to_numpy(),
            "order_placed_at": frame["order_placed_at"].to_numpy(),
            "returned": frame["returned"].to_numpy() if "returned" in frame.columns else np.nan,
            "pickup_at": frame["pickup_at"].to_numpy() if "pickup_at" in frame.columns else np.nan,
        }
    )
    work["_pos"] = np.arange(len(frame))
    for _, group in work.groupby("customer_id", sort=False):
        group = group.sort_values(["order_placed_at", "_pos"])
        times = group["order_placed_at"].to_numpy()
        returned = group["returned"].to_numpy()
        pickup = group["pickup_at"].to_numpy()
        positions = group["_pos"].to_numpy()
        for i in range(len(group)):
            earlier = times[:i] < times[i]
            prior_orders[positions[i]] = float(earlier.sum())
            known_returns = 0
            for j in np.flatnonzero(earlier):
                ret = returned[j]
                picked = pickup[j]
                if pd.isna(ret) or pd.isna(picked):
                    continue
                if float(ret) == 1.0 and picked < times[i]:
                    known_returns += 1
            prior_returns[positions[i]] = known_returns
    frame["pit_prior_orders"] = prior_orders
    frame["pit_prior_returns"] = prior_returns
    rate = np.zeros(len(frame), dtype=float)
    positive = prior_orders > 0
    rate[positive] = prior_returns[positive] / prior_orders[positive]
    frame["pit_prior_return_rate"] = rate
    return frame


def design_matrix(orders: pd.DataFrame, include_history: bool, history_source: str = "supplied") -> pd.DataFrame:
    """Return the model matrix.

    history_source:
    - supplied: CRM prior-count columns on the dispatch snapshot
    - none: no history columns
    - pit: leakage-safe counts built from earlier orders only
    """
    if history_source not in {"supplied", "none", "pit"}:
        raise ValueError(f"Unknown history_source {history_source}")
    frame = orders
    if history_source == "pit":
        renamed = frame.drop(
            columns=[column for column in ("customer_prior_orders", "customer_prior_returns", "prior_return_rate") if column in frame.columns]
        ).rename(
            columns={
                "pit_prior_orders": "customer_prior_orders",
                "pit_prior_returns": "customer_prior_returns",
                "pit_prior_return_rate": "prior_return_rate",
            }
        )
        matrix = renamed[feature_columns(True)].copy()
    elif history_source == "none":
        matrix = frame[feature_columns(False)].copy()
    else:
        matrix = frame[feature_columns(include_history)].copy()
    leaked = [column for column in LEAKY_COLUMNS if column in matrix.columns]
    if leaked:
        raise ValueError(f"Design matrix contains excluded columns: {leaked}")
    return matrix
