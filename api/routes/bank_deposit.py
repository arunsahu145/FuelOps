"""
FastAPI route — Bank Deposits
Handles monthly bank deposit entries (Working Capital, Solar, Truck, Top Up Finance).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import date

from database.engine import get_db
from database.models import BankDeposit
from pydantic import BaseModel

router = APIRouter(prefix="/api/bank-deposit", tags=["Bank Deposits"])


class BankDepositCreate(BaseModel):
    month: int
    year: int
    deposit_date: Optional[date] = None
    working_capital: float = 0.0
    solar: float = 0.0
    truck: float = 0.0
    top_up_finance: float = 0.0
    notes: Optional[str] = None


class BankDepositResponse(BaseModel):
    id: int
    month: int
    year: int
    deposit_date: Optional[date] = None
    working_capital: float
    solar: float
    truck: float
    top_up_finance: float
    total: float
    notes: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/entry", response_model=BankDepositResponse)
def create_bank_deposit(request: BankDepositCreate, db: Session = Depends(get_db)):
    """Record a new bank deposit entry."""
    total = request.working_capital + request.solar + request.truck + request.top_up_finance
    if total <= 0:
        raise HTTPException(status_code=400, detail="At least one deposit amount must be greater than zero")

    deposit = BankDeposit(
        month=request.month,
        year=request.year,
        deposit_date=request.deposit_date,
        working_capital=request.working_capital,
        solar=request.solar,
        truck=request.truck,
        top_up_finance=request.top_up_finance,
        notes=request.notes,
    )
    db.add(deposit)
    db.commit()
    db.refresh(deposit)

    return BankDepositResponse(
        id=deposit.id,
        month=deposit.month,
        year=deposit.year,
        deposit_date=deposit.deposit_date,
        working_capital=deposit.working_capital,
        solar=deposit.solar,
        truck=deposit.truck,
        top_up_finance=deposit.top_up_finance,
        total=deposit.working_capital + deposit.solar + deposit.truck + deposit.top_up_finance,
        notes=deposit.notes,
    )


@router.get("/list")
def list_bank_deposits(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List bank deposits with optional month/year filter."""
    query = db.query(BankDeposit)
    if month is not None:
        query = query.filter(BankDeposit.month == month)
    if year is not None:
        query = query.filter(BankDeposit.year == year)

    deposits = query.order_by(desc(BankDeposit.created_at)).all()
    return [
        {
            "id": d.id,
            "month": d.month,
            "year": d.year,
            "deposit_date": str(d.deposit_date) if d.deposit_date else None,
            "working_capital": d.working_capital,
            "solar": d.solar,
            "truck": d.truck,
            "top_up_finance": d.top_up_finance,
            "total": d.working_capital + d.solar + d.truck + d.top_up_finance,
            "notes": d.notes,
        }
        for d in deposits
    ]


@router.get("/summary")
def get_bank_deposit_summary(
    month: int = Query(...),
    year: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get aggregated bank deposit summary for a month."""
    deposits = db.query(BankDeposit).filter(
        BankDeposit.month == month,
        BankDeposit.year == year,
    ).all()

    total_working_capital = sum(d.working_capital for d in deposits)
    total_solar = sum(d.solar for d in deposits)
    total_truck = sum(d.truck for d in deposits)
    total_top_up = sum(d.top_up_finance for d in deposits)
    grand_total = total_working_capital + total_solar + total_truck + total_top_up

    return {
        "month": month,
        "year": year,
        "total_working_capital": total_working_capital,
        "total_solar": total_solar,
        "total_truck": total_truck,
        "total_top_up_finance": total_top_up,
        "grand_total": grand_total,
        "entry_count": len(deposits),
    }


@router.put("/entry/{deposit_id}", response_model=BankDepositResponse)
def update_bank_deposit(deposit_id: int, request: BankDepositCreate, db: Session = Depends(get_db)):
    """Update an existing bank deposit entry."""
    deposit = db.query(BankDeposit).filter_by(id=deposit_id).first()
    if not deposit:
        raise HTTPException(status_code=404, detail="Bank deposit entry not found")

    total = request.working_capital + request.solar + request.truck + request.top_up_finance
    if total <= 0:
        raise HTTPException(status_code=400, detail="At least one deposit amount must be greater than zero")

    deposit.working_capital = request.working_capital
    deposit.solar = request.solar
    deposit.truck = request.truck
    deposit.top_up_finance = request.top_up_finance
    deposit.notes = request.notes
    if request.deposit_date:
        deposit.deposit_date = request.deposit_date

    db.commit()
    db.refresh(deposit)

    return BankDepositResponse(
        id=deposit.id,
        month=deposit.month,
        year=deposit.year,
        deposit_date=deposit.deposit_date,
        working_capital=deposit.working_capital,
        solar=deposit.solar,
        truck=deposit.truck,
        top_up_finance=deposit.top_up_finance,
        total=deposit.working_capital + deposit.solar + deposit.truck + deposit.top_up_finance,
        notes=deposit.notes,
    )


@router.delete("/entry/{deposit_id}")
def delete_bank_deposit(deposit_id: int, db: Session = Depends(get_db)):
    """Delete a bank deposit entry."""
    deposit = db.query(BankDeposit).filter_by(id=deposit_id).first()
    if not deposit:
        raise HTTPException(status_code=404, detail="Bank deposit entry not found")

    db.delete(deposit)
    db.commit()
    return {"detail": "Bank deposit deleted", "id": deposit_id}
