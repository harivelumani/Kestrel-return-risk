"""Load the task pack, drop duplicate exports, and validate joins.

The client files stay in Document/ (or KESTREL_DATA_DIR). This module does
not write them anywhere else.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import DATA_DIR, FIT_END, VAL_END

ORDER_COMPARE_COLUMNS = (
    "order_placed_at",
    "customer_id",
    "sku",
    "sales_channel",
    "payment_mode",
    "discount_pct",
    "qty",
    "order_value_inr",
    "promised_delivery_days",
    "delivery_pincode",
    "is_gift",
    "customer_prior_orders",
    "customer_prior_returns",
    "delivery_note",
    "last_service_event_type",
    "pickup_scheduled_at",
    "returned",
)


def _read_orders(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Place the Kestrel task pack in {DATA_DIR} "
            "or set KESTREL_DATA_DIR."
        )
    frame = pd.read_csv(path)
    frame["order_placed_at"] = pd.to_datetime(frame["order_placed_at"])
    return frame


def load_reference_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    customers = pd.read_csv(DATA_DIR / "customers.csv")
    products = pd.read_csv(DATA_DIR / "products.csv")
    customers["signup_date"] = pd.to_datetime(customers["signup_date"])
    products["launch_date"] = pd.to_datetime(products["launch_date"])
    if customers["customer_id"].duplicated().any():
        raise ValueError("customers.csv has duplicate customer_id values.")
    if products["sku"].duplicated().any():
        raise ValueError("products.csv has duplicate sku values.")
    return customers, products


def deduplicate_train(train: pd.DataFrame) -> pd.DataFrame:
    """Keep the CRM row. partner_feed is a re-import, not a second order.

    FACT from the email: partner-outlet orders are re-imported, so some
    orders appear twice. The two copies must match on every field except
    source. If they do not, stop rather than silently dropping one.
    """
    if train["order_id"].duplicated().any() is False:
        return train.copy()

    duplicated = train[train["order_id"].duplicated(keep=False)].copy()
    crm = duplicated[duplicated["source"] == "crm"].set_index("order_id")
    feed = duplicated[duplicated["source"] == "partner_feed"].set_index("order_id")
    if len(crm) != len(feed) or not crm.index.equals(feed.index):
        raise ValueError(
            "Duplicate orders are not a clean CRM/partner_feed pair. "
            f"crm={len(crm)} partner_feed={len(feed)}"
        )
    for column in ORDER_COMPARE_COLUMNS:
        if column not in train.columns:
            continue
        left = crm[column]
        right = feed[column]
        if column == "order_placed_at":
            mismatch = left != right
        else:
            mismatch = left.fillna("__NA__").astype(str) != right.fillna("__NA__").astype(str)
        if bool(mismatch.any()):
            raise ValueError(
                f"partner_feed copy differs from CRM on {column} "
                f"for {int(mismatch.sum())} orders. Refusing to drop rows."
            )
    kept = train[train["source"] == "crm"].copy()
    if kept["order_id"].duplicated().any():
        raise ValueError("CRM extract still has duplicate order_id values.")
    return kept.reset_index(drop=True)


def assert_order_value_scale(orders: pd.DataFrame, products: pd.DataFrame) -> None:
    """October 2025 values are exactly 100x list price x qty x discount.

    Every other month matches that formula exactly. Confirmed against
    Tanmay's note about the festive payment gateway.
    """
    merged = orders.merge(products[["sku", "list_price_inr"]], on="sku", how="left")
    if merged["list_price_inr"].isna().any():
        raise ValueError("SKU missing from products.csv while checking order value.")
    expected = merged["list_price_inr"] * merged["qty"] * (1 - merged["discount_pct"] / 100)
    ratio = merged["order_value_inr"] / expected
    october = (merged["order_placed_at"] >= "2025-10-01") & (
        merged["order_placed_at"] < "2025-11-01"
    )
    if not np.allclose(ratio[october], 100):
        raise ValueError("October 2025 order values are not a uniform 100x scale error.")
    if not np.allclose(ratio[~october], 1):
        raise ValueError("Non-October order values do not match list price x qty x discount.")


def join_reference(orders: pd.DataFrame, customers: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    before = len(orders)
    before_ids = orders["order_id"].nunique()
    merged = orders.merge(customers, on="customer_id", how="left", validate="many_to_one")
    merged = merged.merge(products, on="sku", how="left", validate="many_to_one")
    if len(merged) != before or merged["order_id"].nunique() != before_ids:
        raise ValueError(
            f"Join changed order count from {before} rows / {before_ids} ids "
            f"to {len(merged)} rows / {merged['order_id'].nunique()} ids."
        )
    if merged["state"].isna().any() or merged["family"].isna().any():
        missing_customers = int(merged["state"].isna().sum())
        missing_products = int(merged["family"].isna().sum())
        raise ValueError(
            f"Unmatched reference rows: customers={missing_customers} products={missing_products}."
        )
    return merged


def load_labeled_orders() -> pd.DataFrame:
    train = _read_orders("train.csv")
    customers, products = load_reference_tables()
    labeled = deduplicate_train(train)
    assert_order_value_scale(labeled, products)
    labeled = join_reference(labeled, customers, products)
    labeled["pickup_at"] = pd.to_datetime(labeled["pickup_scheduled_at"], errors="coerce")
    return labeled.sort_values(["order_placed_at", "order_id"]).reset_index(drop=True)


def load_test_orders() -> pd.DataFrame:
    test = _read_orders("test_unlabelled.csv")
    if "returned" in test.columns:
        raise ValueError("Test file contains a returned column. Refusing to train on it.")
    if test["order_id"].duplicated().any():
        raise ValueError("Test file has duplicate order_id values.")
    start = test["order_placed_at"].min()
    end = test["order_placed_at"].max()
    if start < pd.Timestamp("2026-07-01") or end >= pd.Timestamp("2026-10-01"):
        raise ValueError(
            f"Test dates {start} to {end} are not the July–September 2026 dispatch window."
        )
    customers, products = load_reference_tables()
    test = join_reference(test, customers, products)
    test["pickup_at"] = pd.to_datetime(test["pickup_scheduled_at"], errors="coerce")
    if test["pickup_at"].notna().any():
        raise ValueError("Test snapshot contains pickup timestamps. Dispatch assumption failed.")
    return test.sort_values(["order_placed_at", "order_id"]).reset_index(drop=True)


def split_fit_val(labeled: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    fit = labeled[labeled["order_placed_at"] < FIT_END].copy()
    val = labeled[
        (labeled["order_placed_at"] >= FIT_END) & (labeled["order_placed_at"] < VAL_END)
    ].copy()
    held_out = labeled[labeled["order_placed_at"] >= VAL_END]
    if len(held_out):
        raise ValueError("Labeled data extends into the test period.")
    if len(fit) + len(val) != len(labeled):
        raise ValueError("Fit and validation do not cover the labeled orders.")
    return fit.reset_index(drop=True), val.reset_index(drop=True)
