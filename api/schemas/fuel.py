"""Pydantic schemas for fuel types and pricing."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── Fuel Type ────────────────────────────────────────────────────────────────

class FuelTypeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    current_purchase_price: Optional[float] = None
    current_selling_price: Optional[float] = None

    class Config:
        from_attributes = True


# ─── Purchase Rate ────────────────────────────────────────────────────────────

class SetPurchaseRateRequest(BaseModel):
    fuel_type_id: int
    price_per_litre: float = Field(..., gt=0, description="Price must be positive")


class PurchaseRateResponse(BaseModel):
    id: int
    fuel_type_id: int
    fuel_name: Optional[str] = None
    price_per_litre: float
    effective_from: datetime

    class Config:
        from_attributes = True


# ─── Selling Rate ─────────────────────────────────────────────────────────────

class SetSellingRateRequest(BaseModel):
    fuel_type_id: int
    price_per_litre: float = Field(..., gt=0, description="Price must be positive")


class SellingRateResponse(BaseModel):
    id: int
    fuel_type_id: int
    fuel_name: Optional[str] = None
    price_per_litre: float
    effective_from: datetime

    class Config:
        from_attributes = True
