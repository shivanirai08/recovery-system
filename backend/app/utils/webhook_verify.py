import hmac
import hashlib
import os

from dotenv import load_dotenv

load_dotenv(".env.local")


def verify_razorpay_signature(raw_body: bytes, signature: str | None) -> None:
    """Verify X-Razorpay-Signature against the raw request body.

    Razorpay signs the exact bytes, so this must run before JSON parsing.
    """
    secret = os.getenv("WEBHOOK_SECRET")
    if not secret:
        raise RuntimeError("WEBHOOK_SECRET is not set")
    if not signature:
        raise ValueError("Missing X-Razorpay-Signature")

    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Invalid webhook signature")
