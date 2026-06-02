"""
FastAPI route — Purchase Management
Handles fuel purchase entries, updates tank stock, and lists purchases.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import date

from database.engine import get_db
from database.models import FuelPurchase, FuelType, FuelPurchaseRate, TankStock
from api.schemas.purchase import PurchaseCreateRequest, PurchaseResponse

router = APIRouter(prefix="/api/purchase", tags=["Purchase Management"])


@router.post("/entry", response_model=PurchaseResponse)
def create_purchase(request: PurchaseCreateRequest, db: Session = Depends(get_db)):
    """
    Record a new fuel purchase, auto-calculates details, and increases tank stock.
    """
    fuel = db.query(FuelType).filter_by(id=request.fuel_type_id, is_active=True).first()
    if not fuel:
        raise HTTPException(status_code=404, detail="Fuel type not found")

    # Get latest purchase price
    rate = db.query(FuelPurchaseRate).filter_by(
        fuel_type_id=fuel.id
    ).order_by(desc(FuelPurchaseRate.effective_from)).first()

    if not rate:
        raise HTTPException(
            status_code=400,
            detail=f"No purchase price set for {fuel.name}. Please set the purchase price first."
        )

    price_per_litre = rate.price_per_litre

    # Calculate missing values
    litres = request.litres_purchased
    total_cost = request.total_cost

    if litres is None and total_cost is None:
        raise HTTPException(
            status_code=400,
            detail="Either litres purchased or total cost must be provided."
        )
    elif litres is not None and total_cost is None:
        total_cost = litres * price_per_litre
    elif litres is None and total_cost is not None:
        litres = total_cost / price_per_litre
    else:
        # Both provided, verify consistency or use provided values
        # If provided cost doesn't match, we can recalculate price_per_litre based on cost/litres
        if litres > 0:
            price_per_litre = total_cost / litres

    # Create fuel purchase record
    purchase = FuelPurchase(
        fuel_type_id=fuel.id,
        purchase_date=request.purchase_date,
        litres_purchased=litres,
        price_per_litre=price_per_litre,
        total_cost=total_cost,
        supplier_name=request.supplier_name,
        notes=request.notes
    )
    db.add(purchase)

    # Update Tank Stock
    stock = db.query(TankStock).filter_by(fuel_type_id=fuel.id).first()
    if not stock:
        stock = TankStock(fuel_type_id=fuel.id, current_stock_litres=0.0)
        db.add(stock)
    stock.current_stock_litres += litres

    db.commit()
    db.refresh(purchase)

    return PurchaseResponse(
        id=purchase.id,
        fuel_type_id=purchase.fuel_type_id,
        fuel_type_name=fuel.name,
        purchase_date=purchase.purchase_date,
        litres_purchased=purchase.litres_purchased,
        price_per_litre=purchase.price_per_litre,
        total_cost=purchase.total_cost,
        supplier_name=purchase.supplier_name,
        notes=purchase.notes,
        created_at=purchase.created_at
    )


@router.get("/list", response_model=List[PurchaseResponse])
def get_purchases(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    fuel_type_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get list of fuel purchases with optional filters."""
    query = db.query(FuelPurchase)
    if start_date:
        query = query.filter(FuelPurchase.purchase_date >= start_date)
    if end_date:
        query = query.filter(FuelPurchase.purchase_date <= end_date)
    if fuel_type_id:
        query = query.filter(FuelPurchase.fuel_type_id == fuel_type_id)

    purchases = query.order_by(desc(FuelPurchase.purchase_date)).all()
    result = []
    for p in purchases:
        fuel = db.query(FuelType).filter_by(id=p.fuel_type_id).first()
        result.append(PurchaseResponse(
            id=p.id,
            fuel_type_id=p.fuel_type_id,
            fuel_type_name=fuel.name if fuel else "Unknown",
            purchase_date=p.purchase_date,
            litres_purchased=p.litres_purchased,
            price_per_litre=p.price_per_litre,
            total_cost=p.total_cost,
            supplier_name=p.supplier_name,
            notes=p.notes,
            created_at=p.created_at
        ))
    return result


@router.delete("/entry/{purchase_id}")
def delete_purchase(purchase_id: int, db: Session = Depends(get_db)):
    """Delete a purchase entry. Reverses tank stock update."""
    purchase = db.query(FuelPurchase).filter_by(id=purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase entry not found")

    # Reverse tank stock
    stock = db.query(TankStock).filter_by(fuel_type_id=purchase.fuel_type_id).first()
    if stock:
        stock.current_stock_litres -= purchase.litres_purchased

    db.delete(purchase)
    db.commit()

    return {"detail": "Purchase deleted", "id": purchase_id}

