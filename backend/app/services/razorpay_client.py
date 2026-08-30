import os
from datetime import datetime, timedelta, timezone

import razorpay
from dotenv import load_dotenv
from razorpay.errors import BadRequestError, ServerError

load_dotenv(".env.local")

# Test Mode has a Payment Link cap — keep expiry short for the demo loop.
PAYMENT_LINK_TTL_HOURS = 24

_client: razorpay.Client | None = None


# This is a singleton client that is used to create payment links.
# It is created once and then reused for the lifetime of the application.
def get_razorpay_client() -> razorpay.Client:
    global _client
    if _client is not None:
        return _client

    key_id = os.getenv("TEST_API_KEY")
    key_secret = os.getenv("TEST_SECRET_KEY")
    if not key_id or not key_secret:
        raise RuntimeError("TEST_API_KEY and TEST_SECRET_KEY must be set")

    _client = razorpay.Client(auth=(key_id, key_secret))
    return _client


# Create a Razorpay Payment Link for an existing RecoverAI payment.
def create_payment_link(
    *,
    amount: int,
    currency: str,
    customer: dict | None,
    reference_id: str,
    description: str | None,
    payment_id: str,
) -> dict:
    expire_by = int(
        (datetime.now(timezone.utc) + timedelta(hours=PAYMENT_LINK_TTL_HOURS)).timestamp()
    )

    payload: dict = {
        "amount": amount,
        "currency": currency,
        "accept_partial": False,
        "expire_by": expire_by,
        "reference_id": reference_id[:40],
        "description": description or "RecoverAI payment recovery",
        "reminder_enable": False,
        "notify": {"sms": False, "email": False},
        "notes": {
            "recoverai_payment_id": payment_id,
        },
    }

    customer_payload = {
        key: value
        for key, value in (customer or {}).items()
        if value
    }
    if customer_payload:
        payload["customer"] = customer_payload

    try:
        data = get_razorpay_client().payment_link.create(payload)
    except BadRequestError as exc:
        raise RuntimeError(f"Razorpay rejected Payment Link: {exc}") from exc
    except ServerError as exc:
        raise RuntimeError(f"Razorpay server error: {exc}") from exc

    return {
        "razorpay_payment_link_id": data["id"],
        "payment_link_url": data["short_url"],
        "razorpay_status": data.get("status"),
        "expire_by": data.get("expire_by", expire_by),
    }
