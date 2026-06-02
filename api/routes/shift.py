"""
FastAPI route — Shift Readings
Handles meter readings per nozzle per shift, auto-calculates sales.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import date, timedelta

from database.engine import get_db
from database.models import (
    ShiftReading, Sale, Nozzle, NozzleAssignment,
    FuelType, FuelSellingRate, TankStock,
    DailyReport, DailyProfitReport, FuelPurchaseRate
)
from api.schemas.shift import (
    ShiftReadingCreateRequest, ShiftReadingResponse, OpeningReadingResponse
)

router = APIRouter(prefix="/api/shift", tags=["Shift Management"])


def get_nozzle_fuel_type(nozzle_id: int, db: Session):
    """Get the fuel type assigned to a nozzle."""
    assignment = db.query(NozzleAssignment).filter_by(
        nozzle_id=nozzle_id, is_active=True
    ).first()
    if not assignment:
        return None, None
    fuel = db.query(FuelType).filter_by(id=assignment.fuel_type_id).first()
    return assignment.fuel_type_id, fuel


def get_current_selling_price(fuel_type_id: int, db: Session) -> Optional[float]:
    """Get the latest selling price for a fuel type."""
    rate = db.query(FuelSellingRate).filter_by(
        fuel_type_id=fuel_type_id
    ).order_by(desc(FuelSellingRate.effective_from)).first()
    return rate.price_per_litre if rate else None


@router.get("/opening-reading", response_model=OpeningReadingResponse)
def get_opening_reading(
    nozzle_id: int,
    shift_number: int,
    reading_date: date,
    db: Session = Depends(get_db)
):
    """
    Get the expected opening reading for a nozzle + shift + date.
    - Shift 2: returns Shift 1's closing reading for same date.
    - Shift 1: returns previous day's Shift 2 closing (or Shift 1 if no Shift 2).
    """
    if shift_number == 2:
        # Look for Shift 1 on same date
        shift1 = db.query(ShiftReading).filter_by(
            nozzle_id=nozzle_id, shift_number=1, reading_date=reading_date
        ).first()
        if shift1:
            return OpeningReadingResponse(
                nozzle_id=nozzle_id,
                shift_number=shift_number,
                reading_date=reading_date,
                opening_reading=shift1.closing_reading,
                source="shift1_closing"
            )
    elif shift_number == 1:
        # Look for previous day's last shift
        prev_date = reading_date - timedelta(days=1)
        prev_shift2 = db.query(ShiftReading).filter_by(
            nozzle_id=nozzle_id, shift_number=2, reading_date=prev_date
        ).first()
        if prev_shift2:
            return OpeningReadingResponse(
                nozzle_id=nozzle_id,
                shift_number=shift_number,
                reading_date=reading_date,
                opening_reading=prev_shift2.closing_reading,
                source="previous_day"
            )
        # Fallback: previous day's shift 1
        prev_shift1 = db.query(ShiftReading).filter_by(
            nozzle_id=nozzle_id, shift_number=1, reading_date=prev_date
        ).first()
        if prev_shift1:
            return OpeningReadingResponse(
                nozzle_id=nozzle_id,
                shift_number=shift_number,
                reading_date=reading_date,
                opening_reading=prev_shift1.closing_reading,
                source="previous_day"
            )

    return OpeningReadingResponse(
        nozzle_id=nozzle_id,
        shift_number=shift_number,
        reading_date=reading_date,
        opening_reading=None,
        source="none"
    )


@router.post("/reading", response_model=ShiftReadingResponse)
def create_shift_reading(
    request: ShiftReadingCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a shift reading. Auto-calculates fuel sold and sales amount.
    Also creates a corresponding Sale record and updates tank stock.
    """
    # Validate nozzle
    nozzle = db.query(Nozzle).filter_by(id=request.nozzle_id).first()
    if not nozzle:
        raise HTTPException(status_code=404, detail="Nozzle not found")

    # Get fuel type from nozzle assignment
    fuel_type_id, fuel = get_nozzle_fuel_type(request.nozzle_id, db)
    if not fuel_type_id:
        raise HTTPException(
            status_code=400,
            detail="No fuel type assigned to this nozzle. Please assign a fuel type first."
        )

    # Get selling price
    selling_price = get_current_selling_price(fuel_type_id, db)
    if selling_price is None:
        raise HTTPException(
            status_code=400,
            detail=f"No selling price set for {fuel.name}. Please set the selling price first."
        )

    # Validate readings
    if request.closing_reading < request.opening_reading:
        raise HTTPException(
            status_code=400,
            detail="Closing reading cannot be less than opening reading"
        )

    # Check for duplicate entry
    existing = db.query(ShiftReading).filter_by(
        nozzle_id=request.nozzle_id,
        shift_number=request.shift_number,
        reading_date=request.reading_date
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Reading already exists for Nozzle {nozzle.nozzle_number}, "
                   f"Shift {request.shift_number} on {request.reading_date}"
        )

    # Calculate
    fuel_sold = request.closing_reading - request.opening_reading
    sales_amount = fuel_sold * selling_price

    # Create shift reading
    reading = ShiftReading(
        nozzle_id=request.nozzle_id,
        shift_number=request.shift_number,
        reading_date=request.reading_date,
        opening_reading=request.opening_reading,
        closing_reading=request.closing_reading,
        fuel_sold_litres=fuel_sold,
        fuel_type_id=fuel_type_id,
        selling_price_per_litre=selling_price,
        sales_amount=sales_amount,
    )
    db.add(reading)
    db.flush()  # Get reading.id

    # Create sale record
    sale = Sale(
        sale_date=request.reading_date,
        fuel_type_id=fuel_type_id,
        nozzle_id=request.nozzle_id,
        shift_number=request.shift_number,
        litres_sold=fuel_sold,
        selling_price=selling_price,
        total_amount=sales_amount,
        shift_reading_id=reading.id,
    )
    db.add(sale)

    # Update tank stock (deduct fuel sold)
    tank = db.query(TankStock).filter_by(fuel_type_id=fuel_type_id).first()
    if tank:
        tank.current_stock_litres -= fuel_sold

    db.commit()
    db.refresh(reading)

    # ── Auto-close daily report after Shift 2 is fully submitted ──
    if request.shift_number == 2:
        try:
            _auto_close_day_if_complete(request.reading_date, db)
        except Exception as e:
            print(f"[AUTO-CLOSE] Warning: auto-close failed for {request.reading_date}: {e}")

    return ShiftReadingResponse(
        id=reading.id,
        nozzle_id=reading.nozzle_id,
        nozzle_number=nozzle.nozzle_number,
        shift_number=reading.shift_number,
        reading_date=reading.reading_date,
        opening_reading=reading.opening_reading,
        closing_reading=reading.closing_reading,
        fuel_sold_litres=reading.fuel_sold_litres,
        fuel_type_id=reading.fuel_type_id,
        fuel_type_name=fuel.name,
        selling_price_per_litre=reading.selling_price_per_litre,
        sales_amount=reading.sales_amount,
        created_at=reading.created_at,
    )


def _auto_close_day_if_complete(reading_date: date, db: Session):
    """
    Auto-close the daily report when all active nozzles have Shift 2 readings.
    Silently skips if already closed or not all nozzles are done.
    """
    # Check if already closed
    existing = db.query(DailyReport).filter_by(report_date=reading_date).first()
    if existing and existing.is_closed:
        return

    # Count active nozzles
    active_nozzles = db.query(Nozzle).filter_by(is_active=True).count()
    if active_nozzles == 0:
        return

    # Count shift 2 readings for this date
    shift2_count = db.query(ShiftReading).filter_by(
        shift_number=2, reading_date=reading_date
    ).count()

    if shift2_count < active_nozzles:
        return  # Not all nozzles done yet

    # ── All nozzles have shift 2 readings → auto-close the day ──
    from sqlalchemy import desc

    # Compute aggregates
    sales = db.query(Sale).filter(Sale.sale_date == reading_date).all()
    total_sales = sum(s.total_amount for s in sales)
    total_litres = sum(s.litres_sold for s in sales)

    from database.models import Payment, Expense
    payments = db.query(Payment).filter(Payment.payment_date == reading_date).all()
    total_payments = sum(p.amount for p in payments)

    expenses = db.query(Expense).filter(Expense.expense_date == reading_date).all()
    total_expenses = sum(e.amount for e in expenses)

    # Purchase cost
    total_purchase_cost = 0.0
    fuel_litres = {}
    for s in sales:
        fuel_litres.setdefault(s.fuel_type_id, 0.0)
        fuel_litres[s.fuel_type_id] += s.litres_sold
    for fid, litres in fuel_litres.items():
        pr = db.query(FuelPurchaseRate).filter(
            FuelPurchaseRate.fuel_type_id == fid
        ).order_by(desc(FuelPurchaseRate.effective_from)).first()
        purchase_price = pr.price_per_litre if pr else 0.0
        # Fallback: use latest actual purchase record
        if purchase_price == 0.0:
            from database.models import FuelPurchase
            latest_purchase = db.query(FuelPurchase).filter(
                FuelPurchase.fuel_type_id == fid
            ).order_by(desc(FuelPurchase.purchase_date)).first()
            if latest_purchase:
                purchase_price = latest_purchase.price_per_litre
        total_purchase_cost += litres * purchase_price

    gross_profit = total_sales - total_purchase_cost
    net_profit = gross_profit - total_expenses

    # Save/update DailyReport
    if existing:
        existing.total_sales = total_sales
        existing.total_expenses = total_expenses
        existing.total_payments = total_payments
        existing.total_litres_sold = total_litres
        existing.is_closed = True
    else:
        daily = DailyReport(
            report_date=reading_date,
            total_sales=total_sales,
            total_expenses=total_expenses,
            total_payments=total_payments,
            total_litres_sold=total_litres,
            is_closed=True,
        )
        db.add(daily)

    # Save/update DailyProfitReport
    existing_profit = db.query(DailyProfitReport).filter_by(report_date=reading_date).first()
    if existing_profit:
        existing_profit.total_sales = total_sales
        existing_profit.total_purchase_cost = total_purchase_cost
        existing_profit.total_expenses = total_expenses
        existing_profit.gross_profit = gross_profit
        existing_profit.net_profit = net_profit
    else:
        profit_report = DailyProfitReport(
            report_date=reading_date,
            total_sales=total_sales,
            total_purchase_cost=total_purchase_cost,
            total_expenses=total_expenses,
            gross_profit=gross_profit,
            net_profit=net_profit,
        )
        db.add(profit_report)

    db.commit()
    print(f"[AUTO-CLOSE] Day {reading_date} auto-closed. Net profit: {net_profit:.2f}")


@router.get("/readings", response_model=List[ShiftReadingResponse])
def get_shift_readings(
    reading_date: Optional[date] = None,
    nozzle_id: Optional[int] = None,
    shift_number: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get shift readings with optional filters."""
    query = db.query(ShiftReading)

    if reading_date:
        query = query.filter(ShiftReading.reading_date == reading_date)
    if nozzle_id:
        query = query.filter(ShiftReading.nozzle_id == nozzle_id)
    if shift_number:
        query = query.filter(ShiftReading.shift_number == shift_number)

    readings = query.order_by(
        desc(ShiftReading.reading_date),
        ShiftReading.shift_number,
        ShiftReading.nozzle_id
    ).all()

    result = []
    for r in readings:
        nozzle = db.query(Nozzle).filter_by(id=r.nozzle_id).first()
        fuel = db.query(FuelType).filter_by(id=r.fuel_type_id).first()
        result.append(ShiftReadingResponse(
            id=r.id,
            nozzle_id=r.nozzle_id,
            nozzle_number=nozzle.nozzle_number if nozzle else None,
            shift_number=r.shift_number,
            reading_date=r.reading_date,
            opening_reading=r.opening_reading,
            closing_reading=r.closing_reading,
            fuel_sold_litres=r.fuel_sold_litres,
            fuel_type_id=r.fuel_type_id,
            fuel_type_name=fuel.name if fuel else None,
            selling_price_per_litre=r.selling_price_per_litre,
            sales_amount=r.sales_amount,
            created_at=r.created_at,
        ))
    return result


@router.delete("/reading/{reading_id}")
def delete_shift_reading(reading_id: int, db: Session = Depends(get_db)):
    """Delete a shift reading and its associated sale record. Restores tank stock."""
    reading = db.query(ShiftReading).filter_by(id=reading_id).first()
    if not reading:
        raise HTTPException(status_code=404, detail="Shift reading not found")

    # Delete associated sale
    sale = db.query(Sale).filter_by(shift_reading_id=reading.id).first()
    if sale:
        db.delete(sale)

    # Restore tank stock
    tank = db.query(TankStock).filter_by(fuel_type_id=reading.fuel_type_id).first()
    if tank:
        tank.current_stock_litres += reading.fuel_sold_litres

    db.delete(reading)
    db.commit()

    return {"detail": "Shift reading deleted", "id": reading_id}

