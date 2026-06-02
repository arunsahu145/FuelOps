"""Pydantic schemas for customer credit and repayment."""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=3)
    address: Optional[str] = None


class CustomerResponse(BaseModel):
    id: int
    customer_code: str
    name: str
    phone: str
    address: Optional[str] = None
    is_active: bool
    created_at: datetime
    total_credit: float = 0.0
    total_repaid: float = 0.0
    outstanding: float = 0.0

    class Config:
        from_attributes = True


class CreditCreate(BaseModel):
    customer_id: int
    credit_date: date
    amount: float = Field(..., gt=0)
    due_date: Optional[date] = None
    remarks: Optional[str] = None


class CreditResponse(BaseModel):
    id: int
    customer_id: int
    customer_code: str
    customer_name: str
    phone: str
    credit_date: date
    amount: float
    due_date: Optional[date] = None
    remarks: Optional[str] = None
    created_at: datetime


class RepaymentCreate(BaseModel):
    customer_id: int
    repayment_date: date
    amount: float = Field(..., gt=0)
    mode: str = Field(..., min_length=1)
    reference_number: Optional[str] = None
    remarks: Optional[str] = None


class RepaymentResponse(BaseModel):
    id: int
    customer_id: int
    customer_code: str
    customer_name: str
    phone: str
    repayment_date: date
    amount: float
    mode: str
    reference_number: Optional[str] = None
    remarks: Optional[str] = None
    outstanding_after: float
    created_at: datetime


class LedgerEntry(BaseModel):
    entry_date: date
    entry_type: str
    debit: float = 0.0
    credit: float = 0.0
    balance: float = 0.0
    mode: Optional[str] = None
    reference_number: Optional[str] = None
    remarks: Optional[str] = None


class OutstandingCustomer(BaseModel):
    customer_id: int
    customer_code: str
    customer_name: str
    phone: str
    total_credit: float
    total_repaid: float
    outstanding: float
    last_credit_date: Optional[date] = None
    last_repayment_date: Optional[date] = None
    oldest_unpaid_date: Optional[date] = None
    overdue_days: int = 0
    status: str


class CreditSummary(BaseModel):
    total_credits_given_today: float = 0.0
    total_credits_outstanding: float = 0.0
    total_repayment_amount_done: float = 0.0
    overdue_customers: int = 0
    total_credits_in_period: float = 0.0
    total_repayments_in_period: float = 0.0


class AgingBucket(BaseModel):
    bucket: str
    customer_count: int
    outstanding: float


class AgingReport(BaseModel):
    as_of: date
    buckets: List[AgingBucket]
    customers: List[OutstandingCustomer]
