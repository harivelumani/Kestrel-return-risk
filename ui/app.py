"""One screen: enter an order, call POST /predict, show the dispatch action."""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import httpx
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Kestrel returns risk", layout="centered")
st.title("Returns risk")
st.caption("Score one order before dispatch. The service uses the frozen logistic model.")

api_url = st.text_input("Prediction service URL", value="http://127.0.0.1:8000")

with st.form("order"):
    order_date = st.date_input("Order date", value=date(2026, 8, 15))
    left, right = st.columns(2)
    with left:
        sales_channel = st.selectbox("Sales channel", ["app", "web", "marketplace", "partner_outlet"])
        payment_mode = st.selectbox("Payment mode", ["prepaid_upi", "prepaid_card", "cod", "emi"])
        is_gift = st.selectbox("Gift order", ["N", "Y"])
        shield_member = st.selectbox("Shield member", ["N", "Y"])
        state = st.selectbox("State", ["MH", "KA", "RJ", "MP", "TS", "TN", "DL", "UP"])
        family = st.selectbox(
            "Product family",
            [
                "Air Fryer",
                "Ceiling Fan",
                "Induction Cooktop",
                "Mixer Grinder",
                "Robot Vacuum",
                "Room Heater",
                "Water Purifier",
            ],
        )
    with right:
        discount_pct = st.number_input("Discount %", min_value=0.0, max_value=100.0, value=10.0)
        qty = st.number_input("Quantity", min_value=1, max_value=10, value=1, step=1)
        promised_delivery_days = st.number_input("Promised delivery days", min_value=1, max_value=30, value=7, step=1)
        delivery_pincode = st.number_input("Delivery PIN (0 if missing)", min_value=0, max_value=999999, value=560001, step=1)
        customer_prior_orders = st.number_input("Prior orders", min_value=0, max_value=100, value=2, step=1)
        customer_prior_returns = st.number_input("Prior returns", min_value=0, max_value=100, value=1, step=1)
        list_price_inr = st.number_input("List price (Rs)", min_value=1.0, max_value=500000.0, value=22000.0)
    signup_date = st.date_input("Customer signup date", value=date(2024, 1, 15))
    launch_date = st.date_input("Product launch date", value=date(2024, 1, 1))
    submitted = st.form_submit_button("Score order")

if submitted:
    payload = {
        "order_placed_at": datetime.combine(order_date, datetime.min.time()).isoformat(),
        "sales_channel": sales_channel,
        "payment_mode": payment_mode,
        "discount_pct": discount_pct,
        "qty": int(qty),
        "promised_delivery_days": int(promised_delivery_days),
        "delivery_pincode": int(delivery_pincode),
        "is_gift": is_gift,
        "customer_prior_orders": int(customer_prior_orders),
        "customer_prior_returns": int(customer_prior_returns),
        "signup_date": signup_date.isoformat(),
        "state": state,
        "shield_member": shield_member,
        "family": family,
        "list_price_inr": list_price_inr,
        "launch_date": launch_date.isoformat(),
    }
    try:
        response = httpx.post(f"{api_url.rstrip('/')}/predict", json=payload, timeout=10.0)
    except httpx.HTTPError:
        st.error("Prediction service is unavailable. Start it with: uvicorn api.main:app --reload")
    else:
        if response.status_code != 200:
            detail = response.json().get("detail", "The service rejected this order.") if response.headers.get("content-type", "").startswith("application/json") else response.text
            st.error(detail if isinstance(detail, str) else "The service rejected this order.")
        else:
            body = response.json()
            st.metric("Return risk", f"{body['risk_score'] * 100:.1f}%")
            st.subheader(body["risk_level"])
            st.write(body["recommended_action"])
            if body.get("shield_handling"):
                st.info(body["shield_handling"])
            st.markdown("**Reasons**")
            for reason in body.get("reasons", []):
                st.write(f"- {reason}")
