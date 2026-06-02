"""Pydantic schemas for sales queries."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class SaleResponse(BaseModel):
    id: int
    sale_date: date
    fuel_type_id: int
    fuel_type_name: Optional[str] = None
    nozzle_id: Optional[int] = None
    nozzle_number: Optional[int] = None
    shift_number: Optional[int] = None
    litres_sold: float
    selling_price: float
    total_amount: float

    class Config:
        from_attributes = True


class DailySalesSummary(BaseModel):
    date: date
    total_litres: float
    total_amount: float
    fuel_breakdown: List[dict] = []
    shift_breakdown: List[dict] = []
    nozzle_breakdown: List[dict] = []


class MonthlySalesSummary(BaseModel):
    month: int
    year: int
    total_litres: float
    total_amount: float
    daily_totals: List[dict] = []
    fuel_breakdown: List[dict] = []
