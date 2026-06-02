"""
FastAPI route — Sales Queries
Daily/monthly sales with fuel-wise, nozzle-wise, shift-wise breakdowns.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import date

from database.engine import get_db
from database.models import Sale, FuelType, Nozzle
from api.schemas.sales import SaleResponse, DailySalesSummary, MonthlySalesSummary
from utils.helpers import get_month_range

router = APIRouter(prefix="/api/sales", tags=["Sales"])


@router.get("/daily", response_model=DailySalesSummary)
def get_daily_sales(
    sale_date: date = Query(default=None),
    fuel_type_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get daily sales summary with breakdowns."""
    if sale_date is None:
        sale_date = date.today()

    query = db.query(Sale).filter(Sale.sale_date == sale_date)
    if fuel_type_id:
        query = query.filter(Sale.fuel_type_id == fuel_type_id)

    sales = query.all()

    total_litres = sum(s.litres_sold for s in sales)
    total_amount = sum(s.total_amount for s in sales)

    # Fuel breakdown
    fuel_breakdown = []
    fuel_groups = {}
    for s in sales:
        fuel = db.query(FuelType).filter_by(id=s.fuel_type_id).first()
        fname = fuel.name if fuel else "Unknown"
        if fname not in fuel_groups:
            fuel_groups[fname] = {"fuel_type": fname, "litres": 0.0, "amount": 0.0}
        fuel_groups[fname]["litres"] += s.litres_sold
        fuel_groups[fname]["amount"] += s.total_amount
    fuel_breakdown = list(fuel_groups.values())

    # Shift breakdown
    shift_breakdown = []
    shift_groups = {}
    for s in sales:
        sn = s.shift_number or 0
        if sn not in shift_groups:
            shift_groups[sn] = {"shift": sn, "litres": 0.0, "amount": 0.0}
        shift_groups[sn]["litres"] += s.litres_sold
        shift_groups[sn]["amount"] += s.total_amount
    shift_breakdown = list(shift_groups.values())

    # Nozzle breakdown
    nozzle_breakdown = []
    nozzle_groups = {}
    for s in sales:
        nozzle = db.query(Nozzle).filter_by(id=s.nozzle_id).first()
        nn = nozzle.nozzle_number if nozzle else 0
        if nn not in nozzle_groups:
            nozzle_groups[nn] = {"nozzle": nn, "litres": 0.0, "amount": 0.0}
        nozzle_groups[nn]["litres"] += s.litres_sold
        nozzle_groups[nn]["amount"] += s.total_amount
    nozzle_breakdown = list(nozzle_groups.values())

    return DailySalesSummary(
        date=sale_date,
        total_litres=total_litres,
        total_amount=total_amount,
        fuel_breakdown=fuel_breakdown,
        shift_breakdown=shift_breakdown,
        nozzle_breakdown=nozzle_breakdown,
    )


@router.get("/monthly", response_model=MonthlySalesSummary)
def get_monthly_sales(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    fuel_type_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get monthly sales summary with daily totals and fuel breakdown."""
    first_day, last_day = get_month_range(year, month)

    query = db.query(Sale).filter(
        Sale.sale_date >= first_day,
        Sale.sale_date <= last_day
    )
    if fuel_type_id:
        query = query.filter(Sale.fuel_type_id == fuel_type_id)

    sales = query.all()

    total_litres = sum(s.litres_sold for s in sales)
    total_amount = sum(s.total_amount for s in sales)

    # Daily totals
    daily_totals = {}
    for s in sales:
        d = str(s.sale_date)
        if d not in daily_totals:
            daily_totals[d] = {"date": d, "litres": 0.0, "amount": 0.0}
        daily_totals[d]["litres"] += s.litres_sold
        daily_totals[d]["amount"] += s.total_amount

    # Fuel breakdown
    fuel_groups = {}
    for s in sales:
        fuel = db.query(FuelType).filter_by(id=s.fuel_type_id).first()
        fname = fuel.name if fuel else "Unknown"
        if fname not in fuel_groups:
            fuel_groups[fname] = {"fuel_type": fname, "litres": 0.0, "amount": 0.0}
        fuel_groups[fname]["litres"] += s.litres_sold
        fuel_groups[fname]["amount"] += s.total_amount

    return MonthlySalesSummary(
        month=month,
        year=year,
        total_litres=total_litres,
        total_amount=total_amount,
        daily_totals=list(daily_totals.values()),
        fuel_breakdown=list(fuel_groups.values()),
    )


@router.get("/list", response_model=List[SaleResponse])
def get_sales_list(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    fuel_type_id: Optional[int] = None,
    nozzle_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get filtered list of individual sale records."""
    query = db.query(Sale)
    if start_date:
        query = query.filter(Sale.sale_date >= start_date)
    if end_date:
        query = query.filter(Sale.sale_date <= end_date)
    if fuel_type_id:
        query = query.filter(Sale.fuel_type_id == fuel_type_id)
    if nozzle_id:
        query = query.filter(Sale.nozzle_id == nozzle_id)

    sales = query.order_by(desc(Sale.sale_date)).limit(500).all()

    result = []
    for s in sales:
        fuel = db.query(FuelType).filter_by(id=s.fuel_type_id).first()
        nozzle = db.query(Nozzle).filter_by(id=s.nozzle_id).first()
        result.append(SaleResponse(
            id=s.id,
            sale_date=s.sale_date,
            fuel_type_id=s.fuel_type_id,
            fuel_type_name=fuel.name if fuel else None,
            nozzle_id=s.nozzle_id,
            nozzle_number=nozzle.nozzle_number if nozzle else None,
            shift_number=s.shift_number,
            litres_sold=s.litres_sold,
            selling_price=s.selling_price,
            total_amount=s.total_amount,
        ))
    return result
