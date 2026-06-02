"""
FastAPI route — Fuel Management
CRUD for fuel types, purchase rates, and selling rates.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from database.engine import get_db
from database.models import FuelType, FuelPurchaseRate, FuelSellingRate
from api.schemas.fuel import (
    FuelTypeResponse, SetPurchaseRateRequest, PurchaseRateResponse,
    SetSellingRateRequest, SellingRateResponse
)

router = APIRouter(prefix="/api/fuel", tags=["Fuel Management"])


# ─── Fuel Types ───────────────────────────────────────────────────────────────

@router.get("/types", response_model=List[FuelTypeResponse])
def get_fuel_types(db: Session = Depends(get_db)):
    """Get all fuel types with their current prices."""
    fuels = db.query(FuelType).filter_by(is_active=True).all()
    result = []
    for fuel in fuels:
        # Get latest purchase rate
        purchase_rate = db.query(FuelPurchaseRate).filter_by(
            fuel_type_id=fuel.id
        ).order_by(desc(FuelPurchaseRate.effective_from)).first()

        # Get latest selling rate
        selling_rate = db.query(FuelSellingRate).filter_by(
            fuel_type_id=fuel.id
        ).order_by(desc(FuelSellingRate.effective_from)).first()

        result.append(FuelTypeResponse(
            id=fuel.id,
            name=fuel.name,
            description=fuel.description,
            is_active=fuel.is_active,
            current_purchase_price=purchase_rate.price_per_litre if purchase_rate else None,
            current_selling_price=selling_rate.price_per_litre if selling_rate else None,
        ))
    return result


@router.get("/types/{fuel_id}", response_model=FuelTypeResponse)
def get_fuel_type(fuel_id: int, db: Session = Depends(get_db)):
    """Get a specific fuel type with current prices."""
    fuel = db.query(FuelType).filter_by(id=fuel_id, is_active=True).first()
    if not fuel:
        raise HTTPException(status_code=404, detail="Fuel type not found")

    purchase_rate = db.query(FuelPurchaseRate).filter_by(
        fuel_type_id=fuel.id
    ).order_by(desc(FuelPurchaseRate.effective_from)).first()

    selling_rate = db.query(FuelSellingRate).filter_by(
        fuel_type_id=fuel.id
    ).order_by(desc(FuelSellingRate.effective_from)).first()

    return FuelTypeResponse(
        id=fuel.id,
        name=fuel.name,
        description=fuel.description,
        is_active=fuel.is_active,
        current_purchase_price=purchase_rate.price_per_litre if purchase_rate else None,
        current_selling_price=selling_rate.price_per_litre if selling_rate else None,
    )


# ─── Purchase Rates ──────────────────────────────────────────────────────────

@router.post("/purchase-rate", response_model=PurchaseRateResponse)
def set_purchase_rate(request: SetPurchaseRateRequest, db: Session = Depends(get_db)):
    """Set a new purchase price for a fuel type."""
    fuel = db.query(FuelType).filter_by(id=request.fuel_type_id).first()
    if not fuel:
        raise HTTPException(status_code=404, detail="Fuel type not found")

    rate = FuelPurchaseRate(
        fuel_type_id=request.fuel_type_id,
        price_per_litre=request.price_per_litre,
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)

    return PurchaseRateResponse(
        id=rate.id,
        fuel_type_id=rate.fuel_type_id,
        fuel_name=fuel.name,
        price_per_litre=rate.price_per_litre,
        effective_from=rate.effective_from,
    )


@router.get("/purchase-rates/{fuel_id}", response_model=List[PurchaseRateResponse])
def get_purchase_rate_history(fuel_id: int, db: Session = Depends(get_db)):
    """Get purchase rate history for a fuel type."""
    rates = db.query(FuelPurchaseRate).filter_by(
        fuel_type_id=fuel_id
    ).order_by(desc(FuelPurchaseRate.effective_from)).all()

    fuel = db.query(FuelType).filter_by(id=fuel_id).first()
    return [
        PurchaseRateResponse(
            id=r.id, fuel_type_id=r.fuel_type_id, fuel_name=fuel.name if fuel else None,
            price_per_litre=r.price_per_litre, effective_from=r.effective_from,
        ) for r in rates
    ]


# ─── Selling Rates ───────────────────────────────────────────────────────────

@router.post("/selling-rate", response_model=SellingRateResponse)
def set_selling_rate(request: SetSellingRateRequest, db: Session = Depends(get_db)):
    """Set a new selling price for a fuel type."""
    fuel = db.query(FuelType).filter_by(id=request.fuel_type_id).first()
    if not fuel:
        raise HTTPException(status_code=404, detail="Fuel type not found")

    rate = FuelSellingRate(
        fuel_type_id=request.fuel_type_id,
        price_per_litre=request.price_per_litre,
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)

    return SellingRateResponse(
        id=rate.id,
        fuel_type_id=rate.fuel_type_id,
        fuel_name=fuel.name,
        price_per_litre=rate.price_per_litre,
        effective_from=rate.effective_from,
    )


@router.get("/selling-rates/{fuel_id}", response_model=List[SellingRateResponse])
def get_selling_rate_history(fuel_id: int, db: Session = Depends(get_db)):
    """Get selling rate history for a fuel type."""
    rates = db.query(FuelSellingRate).filter_by(
        fuel_type_id=fuel_id
    ).order_by(desc(FuelSellingRate.effective_from)).all()

    fuel = db.query(FuelType).filter_by(id=fuel_id).first()
    return [
        SellingRateResponse(
            id=r.id, fuel_type_id=r.fuel_type_id, fuel_name=fuel.name if fuel else None,
            price_per_litre=r.price_per_litre, effective_from=r.effective_from,
        ) for r in rates
    ]


@router.delete("/purchase-rate/{rate_id}")
def delete_purchase_rate(rate_id: int, db: Session = Depends(get_db)):
    """Delete a purchase rate history entry."""
    rate = db.query(FuelPurchaseRate).filter_by(id=rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Purchase rate not found")
    db.delete(rate)
    db.commit()
    return {"detail": "Purchase rate deleted", "id": rate_id}


@router.delete("/selling-rate/{rate_id}")
def delete_selling_rate(rate_id: int, db: Session = Depends(get_db)):
    """Delete a selling rate history entry."""
    rate = db.query(FuelSellingRate).filter_by(id=rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Selling rate not found")
    db.delete(rate)
    db.commit()
    return {"detail": "Selling rate deleted", "id": rate_id}

