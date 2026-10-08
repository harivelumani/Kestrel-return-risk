"""Dispatch return-risk service. Loads the frozen logistic pipeline."""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from src.service import ModelNotAvailable, score_record

app = FastAPI(title="Kestrel returns risk", version="1.0")

CHANNELS = {"app", "web", "marketplace", "partner_outlet"}
PAYMENTS = {"prepaid_upi", "prepaid_card", "cod", "emi"}
STATES = {"MH", "KA", "RJ", "MP", "TS", "TN", "DL", "UP"}
FAMILIES = {
    "Air Fryer",
    "Ceiling Fan",
    "Induction Cooktop",
    "Mixer Grinder",
    "Robot Vacuum",
    "Room Heater",
    "Water Purifier",
}
YES_NO = {"Y", "N"}


class OrderIn(BaseModel):
    order_placed_at: datetime
    sales_channel: str
    payment_mode: str
    discount_pct: float = Field(ge=0, le=100)
    qty: int = Field(ge=1, le=10)
    promised_delivery_days: int = Field(ge=1, le=30)
    delivery_pincode: int = Field(ge=0, le=999999)
    is_gift: str
    customer_prior_orders: int = Field(ge=0, le=100)
    customer_prior_returns: int = Field(ge=0, le=100)
    signup_date: date
    state: str
    shield_member: str
    family: str
    list_price_inr: float = Field(gt=0, le=500000)
    launch_date: date

    @field_validator("sales_channel")
    @classmethod
    def channel(cls, value: str) -> str:
        if value not in CHANNELS:
            raise ValueError(f"sales_channel must be one of {sorted(CHANNELS)}")
        return value

    @field_validator("payment_mode")
    @classmethod
    def payment(cls, value: str) -> str:
        if value not in PAYMENTS:
            raise ValueError(f"payment_mode must be one of {sorted(PAYMENTS)}")
        return value

    @field_validator("state")
    @classmethod
    def state_code(cls, value: str) -> str:
        if value not in STATES:
            raise ValueError(f"state must be one of {sorted(STATES)}")
        return value

    @field_validator("family")
    @classmethod
    def family_name(cls, value: str) -> str:
        if value not in FAMILIES:
            raise ValueError(f"family must be one of {sorted(FAMILIES)}")
        return value

    @field_validator("is_gift", "shield_member")
    @classmethod
    def yes_no(cls, value: str) -> str:
        if value not in YES_NO:
            raise ValueError("value must be Y or N")
        return value

    @model_validator(mode="after")
    def consistent(self) -> "OrderIn":
        if self.customer_prior_returns > self.customer_prior_orders:
            raise ValueError("customer_prior_returns cannot exceed customer_prior_orders")
        if self.launch_date > self.order_placed_at.date():
            raise ValueError("launch_date is after the order date")
        return self


def _plain_validation_message(exc: RequestValidationError) -> str:
    missing = []
    invalid = []
    for error in exc.errors():
        parts = [str(item) for item in error.get("loc", []) if item != "body"]
        field = ".".join(parts) or "request"
        if error.get("type") == "missing":
            missing.append(field)
        else:
            invalid.append(f"{field}: {error.get('msg')}")
    if missing:
        return "Missing required field: " + ", ".join(missing)
    return "Invalid value. " + "; ".join(invalid)


@app.exception_handler(RequestValidationError)
async def validation_handler(_request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": _plain_validation_message(exc)})


@app.exception_handler(Exception)
async def unexpected_handler(_request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(
        status_code=500,
        content={"detail": "The prediction service could not score this order."},
    )


@app.get("/health")
def health():
    try:
        score_record  # imported
        from src.service import cached_model

        cached_model()
    except ModelNotAvailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok"}


@app.post("/predict")
def predict(order: OrderIn):
    try:
        return score_record(order.model_dump())
    except ModelNotAvailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
