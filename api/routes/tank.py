"""
FastAPI route — Tank Stock Management
Provides endpoints to fetch and reconcile fuel tank stock.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database.engine import get_db
from database.models import TankStock, FuelType
from api.schemas.dashboard import TankStockResponse

router = APIRouter(prefix="/api/tank", tags=["Tank Stock Management"])


@router.get("/stock", response_model=List[TankStockResponse])
def get_tank_stock(db: Session = Depends(get_db)):
    """Fetch current stock levels for all active fuel types."""
    stocks = db.query(TankStock).all()
    result = []
    for s in stocks:
        fuel = db.query(FuelType).filter_by(id=s.fuel_type_id).first()
        if fuel and fuel.is_active:
            result.append(TankStockResponse(
                fuel_type_id=s.fuel_type_id,
                fuel_type_name=fuel.name,
                current_stock_litres=s.current_stock_litres,
                last_updated=s.last_updated.strftime("%d-%m-%Y %H:%M") if s.last_updated else None
            ))
    return result


@router.post("/reconcile/{fuel_type_id}", response_model=TankStockResponse)
def reconcile_tank_stock(
    fuel_type_id: int,
    litres: float,
    db: Session = Depends(get_db)
):
    """
    Manually adjust tank stock (e.g. after dip reading calibrations or evaporation).
    """
    fuel = db.query(FuelType).filter_by(id=fuel_type_id, is_active=True).first()
    if not fuel:
        raise HTTPException(status_code=404, detail="Fuel type not found")

    stock = db.query(TankStock).filter_by(fuel_type_id=fuel_type_id).first()
    if not stock:
        stock = TankStock(fuel_type_id=fuel_type_id, current_stock_litres=litres)
        db.add(stock)
    else:
        stock.current_stock_litres = litres
        stock.last_updated = datetime.now()

    db.commit()
    db.refresh(stock)

    return TankStockResponse(
        fuel_type_id=stock.fuel_type_id,
        fuel_type_name=fuel.name,
        current_stock_litres=stock.current_stock_litres,
        last_updated=stock.last_updated.strftime("%d-%m-%Y %H:%M")
    )
