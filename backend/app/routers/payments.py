from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from app.db import get_db
from app.models.payment import PaymentCreate, PaymentOut

router = APIRouter(tags=["payments"])

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
    return PaymentOut(id=str(result.inserted_id), **{k: doc[k] for k in [
        "amount", "currency", "customer", "reference_id", "description",
        "status", "razorpay_payment_link_id", "payment_link_url",
        "created_at", "updated_at",
    ]})

@router.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: str):
    db = get_db()
    if not ObjectId.is_valid(payment_id):
        raise HTTPException(400, "Invalid payment id")
    doc = db["payments"].find_one({"_id": ObjectId(payment_id)})
    if not doc:
        raise HTTPException(404, "Payment not found")
    doc["id"] = str(doc.pop("_id"))
    doc.pop("failure_reason", None)
    return PaymentOut(
        id=doc["id"],
        **{k: doc[k] for k in [
            "amount", "currency", "customer", "reference_id", "description",
            "status", "razorpay_payment_link_id", "payment_link_url",
            "created_at", "updated_at",
        ]}
)