from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.db import get_db
from app.models.payment import PaymentCreate, PaymentOut
from app.services.razorpay_client import create_payment_link

router = APIRouter(tags=["payments"])

PAYMENT_OUT_FIELDS = (
    "amount",
    "currency",
    "customer",
    "reference_id",
    "description",
    "status",
    "razorpay_payment_link_id",
    "payment_link_url",
    "last_error",
    "created_at",
    "updated_at",
)


# Convert a MongoDB document to a PaymentOut object.
def _to_payment_out(doc: dict) -> PaymentOut:
    return PaymentOut(
        id=str(doc["_id"]),
        **{field: doc.get(field) for field in PAYMENT_OUT_FIELDS},
    )


# Get a payment document from the database or raise a 404 error.
def _get_payment_or_404(payment_id: str) -> dict:
    if not ObjectId.is_valid(payment_id):
        raise HTTPException(400, "Invalid payment id")
    doc = get_db()["payments"].find_one({"_id": ObjectId(payment_id)})
    if not doc:
        raise HTTPException(404, "Payment not found")
    return doc


# Create a new payment document in the database.
@router.post("/payments", response_model=PaymentOut)
def create_payment(payment: PaymentCreate):
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = payment.model_dump()
    doc.update({
        "status": "created",
        "razorpay_payment_link_id": None,
        "payment_link_url": None,
        "created_at": now,
        "updated_at": now,
    })
    result = db["payments"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_payment_out(doc)


# Get a payment document from the database or raise a 404 error.
@router.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: str):
    return _to_payment_out(_get_payment_or_404(payment_id))


# Create a Razorpay Payment Link for an existing RecoverAI payment.
@router.post("/payments/{payment_id}/payment-link", response_model=PaymentOut)
def create_link_for_payment(payment_id: str):
    db = get_db()
    doc = _get_payment_or_404(payment_id)

    if doc.get("status") == "paid":
        raise HTTPException(409, "Payment already recovered")
    if doc.get("razorpay_payment_link_id") and doc.get("payment_link_url"):
        return _to_payment_out(doc)

    try:
        link = create_payment_link(
            amount=doc["amount"],
            currency=doc.get("currency", "INR"),
            customer=doc.get("customer"),
            reference_id=doc.get("reference_id") or payment_id,
            description=doc.get("description"),
            payment_id=payment_id,
        )
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc

    now = datetime.now(timezone.utc)
    db["payments"].update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "razorpay_payment_link_id": link["razorpay_payment_link_id"],
            "payment_link_url": link["payment_link_url"],
            "status": "link_created",
            "updated_at": now,
        }},
    )
    doc.update({
        "razorpay_payment_link_id": link["razorpay_payment_link_id"],
        "payment_link_url": link["payment_link_url"],
        "status": "link_created",
        "updated_at": now,
    })
    return _to_payment_out(doc)
