"""Pydantic schemas for payment collections."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class PaymentCreateRequest(BaseModel):
    payment_date: date
    shift_number: Optional[int] = None  # 1 or 2
    payment_method: str  # Cash, Paytm, PhonePe, CCMS
    amount: float = Field(..., gt=0)
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    payment_date: date
    shift_number: Optional[int] = None
    payment_method: str
    amount: float
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentSummary(BaseModel):
    date: date
    total_cash: float = 0.0
    total_paytm: float = 0.0
    total_phonepe: float = 0.0
    total_ccms: float = 0.0
    grand_total: float = 0.0
