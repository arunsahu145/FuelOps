"""Pydantic schemas for expenses."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class ExpenseCreateRequest(BaseModel):
    expense_date: date
    category: str
    amount: float = Field(..., gt=0)
    description: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: int
    expense_date: date
    category: str
    amount: float
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ExpenseSummary(BaseModel):
    date: date
    total_amount: float = 0.0
    category_breakdown: list = []
