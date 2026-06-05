"""
FastAPI route — Payment Collections
Handles recording collections (Cash, Paytm, PhonePe, CCMS) per shift and queries.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import date

from database.engine import get_db
from database.models import Payment
from api.schemas.payment import PaymentCreateRequest, PaymentResponse, PaymentSummary

router = APIRouter(prefix="/api/payment", tags=["Payment Collections"])


@router.post("/entry", response_model=PaymentResponse)
def create_payment(request: PaymentCreateRequest, db: Session = Depends(get_db)):
    """Record a new payment collection."""
    # Validate payment method
    valid_methods = ["Cash", "Paytm", "PhonePe", "CCMS", "Commission"]
    if request.payment_method not in valid_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment method. Must be one of {valid_methods}"
        )

    # Validate shift number
    if request.shift_number is not None and request.shift_number not in [1, 2]:
        raise HTTPException(
            status_code=400,
            detail="Shift number must be 1 or 2"
        )

    payment = Payment(
        payment_date=request.payment_date,
        shift_number=request.shift_number,
        payment_method=request.payment_method,
        amount=request.amount,
        notes=request.notes
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return PaymentResponse(
        id=payment.id,
        payment_date=payment.payment_date,
        shift_number=payment.shift_number,
        payment_method=payment.payment_method,
        amount=payment.amount,
        notes=payment.notes,
        created_at=payment.created_at
    )


@router.get("/list", response_model=List[PaymentResponse])
def get_payments(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    payment_method: Optional[str] = None,
    shift_number: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List payment collections with optional filters."""
    query = db.query(Payment)
    if start_date:
        query = query.filter(Payment.payment_date >= start_date)
    if end_date:
        query = query.filter(Payment.payment_date <= end_date)
    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)
    if shift_number is not None:
        query = query.filter(Payment.shift_number == shift_number)

    payments = query.order_by(desc(Payment.payment_date), Payment.shift_number).all()
    return [
        PaymentResponse(
            id=p.id,
            payment_date=p.payment_date,
            shift_number=p.shift_number,
            payment_method=p.payment_method,
            amount=p.amount,
            notes=p.notes,
            created_at=p.created_at
        ) for p in payments
    ]


@router.get("/summary", response_model=PaymentSummary)
def get_payment_summary(
    payment_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get payment collections summary for a specific date."""
    if payment_date is None:
        payment_date = date.today()

    payments = db.query(Payment).filter(Payment.payment_date == payment_date).all()

    total_cash = sum(p.amount for p in payments if p.payment_method == "Cash")
    total_paytm = sum(p.amount for p in payments if p.payment_method == "Paytm")
    total_phonepe = sum(p.amount for p in payments if p.payment_method == "PhonePe")
    total_ccms = sum(p.amount for p in payments if p.payment_method == "CCMS")
    grand_total = total_cash + total_paytm + total_phonepe + total_ccms

    return PaymentSummary(
        date=payment_date,
        total_cash=total_cash,
        total_paytm=total_paytm,
        total_phonepe=total_phonepe,
        total_ccms=total_ccms,
        grand_total=grand_total
    )


@router.delete("/entry/{payment_id}")
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    """Delete a payment collection entry."""
    payment = db.query(Payment).filter_by(id=payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment entry not found")

    db.delete(payment)
    db.commit()

    return {"detail": "Payment deleted", "id": payment_id}
