from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

PaymentStatus = Literal[
    "created",
    "link_created",
    "waiting_for_payment",
    "paid",
    "failed",
    "expired",
]

class CustomerInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None

class PaymentCreate(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in paise, e.g. 50000 = ₹500")
    currency: str = "INR"
    customer: CustomerInfo
    reference_id: Optional[str] = None
    description: Optional[str] = None
    failure_reason: Optional[str] = None  # later recovery ke liye useful

class PaymentOut(BaseModel):
    id: str
    amount: int
    currency: str
    customer: CustomerInfo
    reference_id: Optional[str] = None
    description: Optional[str] = None
    status: PaymentStatus
    razorpay_payment_link_id: Optional[str] = None
    payment_link_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime