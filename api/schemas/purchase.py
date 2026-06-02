"""Pydantic schemas for fuel purchases."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class PurchaseCreateRequest(BaseModel):
    fuel_type_id: int
    purchase_date: date
    litres_purchased: Optional[float] = Field(None, gt=0)
    total_cost: Optional[float] = Field(None, gt=0)
    supplier_name: Optional[str] = None
    notes: Optional[str] = None


class PurchaseResponse(BaseModel):
    id: int
    fuel_type_id: int
    fuel_type_name: Optional[str] = None
    purchase_date: date
    litres_purchased: float
    price_per_litre: float
    total_cost: float
    supplier_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
