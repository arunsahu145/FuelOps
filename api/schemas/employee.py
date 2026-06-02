"""
Petrol Pump Finance Manager ERP — Employee Schemas
Pydantic models for employee CRUD operations.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class EmployeeCreate(BaseModel):
    name: str
    age: Optional[int] = None
    phone: Optional[str] = None
    monthly_salary: float = 0.0


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    monthly_salary: Optional[float] = None
    is_active: Optional[bool] = None


class EmployeeResponse(BaseModel):
    id: int
    name: str
    age: Optional[int] = None
    phone: Optional[str] = None
    monthly_salary: float
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmployeeSalaryPaymentCreate(BaseModel):
    amount: float
    paid_date: Optional[date] = None
