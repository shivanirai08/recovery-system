from fastapi import APIRouter

router = APIRouter()

@router.post("/payments")
async def create_payment(payment: PaymentCreate):
    doc = payment.model_dump() + { "status": "created" } + { "created_at": datetime.now() }
    inserted = db["payments"].insert_one(doc)
    return PaymentOut(
        id=str(inserted.inserted_id),
        **doc,
    )


@router.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    return {"message": "Payment retrieved successfully"}
