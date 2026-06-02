"""Pydantic schemas for shift readings."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class ShiftReadingCreateRequest(BaseModel):
    nozzle_id: int
    shift_number: int = Field(..., ge=1, le=2)
    reading_date: date
    opening_reading: float = Field(..., ge=0)
    closing_reading: float = Field(..., ge=0)


class ShiftReadingResponse(BaseModel):
    id: int
    nozzle_id: int
    nozzle_number: Optional[int] = None
    shift_number: int
    reading_date: date
    opening_reading: float
    closing_reading: float
    fuel_sold_litres: float
    fuel_type_id: int
    fuel_type_name: Optional[str] = None
    selling_price_per_litre: float
    sales_amount: float
    created_at: datetime

    class Config:
        from_attributes = True


class OpeningReadingResponse(BaseModel):
    """Returns the expected opening reading for a nozzle (from previous shift/day)."""
    nozzle_id: int
    shift_number: int
    reading_date: date
    opening_reading: Optional[float] = None
    source: str = "none"  # 'shift1_closing', 'previous_day', 'none'
