"""
Petrol Pump Finance Manager ERP — Report Schemas
Pydantic models for daily/monthly reports, salaries, and monthly expenses.
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime


# ═══════════════════════════════════════════════════════════════════════════════
# DAILY REPORT
# ═══════════════════════════════════════════════════════════════════════════════

class FuelSalesBreakdown(BaseModel):
    fuel_type: str
    litres_sold: float
    sales_amount: float
    purchase_cost_per_litre: float
    selling_price_per_litre: float
    profit: float


class NozzleSalesBreakdown(BaseModel):
    nozzle_number: int
    fuel_type: str
    shift_number: int
    litres_sold: float
    sales_amount: float


class PaymentBreakdown(BaseModel):
    method: str
    amount: float


class ExpenseBreakdown(BaseModel):
    category: str
    amount: float


class SalaryBreakdown(BaseModel):
    employee_name: str
    amount: float
    paid_date: date


class DailyReportSummary(BaseModel):
    report_date: date
    is_closed: bool = False

    # Sales
    total_sales: float
    total_litres_sold: float
    fuel_breakdown: List[FuelSalesBreakdown]
    nozzle_breakdown: List[NozzleSalesBreakdown]

    # Payments
    total_payments: float
    payment_breakdown: List[PaymentBreakdown]
    cash_collection: float = 0.0
    expected_cash_collection: float = 0.0
    payment_shortfall: float  # positive = cash surplus, negative = cash deficit

    # Expenses
    total_expenses: float
    expense_breakdown: List[ExpenseBreakdown]
    total_salaries: float = 0.0
    salary_breakdown: List[SalaryBreakdown] = []

    # Profit
    gross_profit: float  # sales - purchase cost
    net_profit: float    # gross_profit - expenses
    credit_outstanding: float = 0.0
    credit_received: float = 0.0


class DailyCloseResponse(BaseModel):
    report_date: date
    status: str
    total_sales: float
    total_expenses: float
    total_payments: float
    net_profit: float


# ═══════════════════════════════════════════════════════════════════════════════
# MONTHLY REPORT
# ═══════════════════════════════════════════════════════════════════════════════

class MonthlyFuelBreakdown(BaseModel):
    fuel_type: str
    litres_sold: float
    sales_amount: float
    purchase_cost: float
    profit: float


class EmployeeSalaryEntry(BaseModel):
    employee_name: str
    designation: Optional[str] = None
    monthly_salary: float
    paid_date: Optional[date] = None


class EmployeeSalaryResponse(BaseModel):
    id: int
    employee_name: str
    designation: Optional[str] = None
    monthly_salary: float
    month: int
    year: int
    is_paid: bool
    paid_date: Optional[date] = None


class MonthlyExpenseEntry(BaseModel):
    category: str
    amount: float
    description: Optional[str] = None


class MonthlyExpenseResponse(BaseModel):
    id: int
    category: str
    amount: float
    description: Optional[str] = None
    month: int
    year: int


class MonthlyReportSummary(BaseModel):
    month: int
    year: int
    is_closed: bool = False

    # Sales
    total_sales: float
    total_litres_sold: float
    fuel_breakdown: List[MonthlyFuelBreakdown]

    # Purchases
    total_purchase_cost: float
    total_actual_purchases: float = 0.0
    total_actual_litres_purchased: float = 0.0

    # Payments
    total_payments: float = 0.0
    payment_breakdown: List[PaymentBreakdown] = []
    cash_collection: float = 0.0
    expected_cash_collection: float = 0.0
    payment_shortfall: float = 0.0

    # Expenses
    total_daily_expenses: float
    total_monthly_expenses: float
    total_salaries: float

    # Profit
    gross_profit: float      # sales - purchase cost
    net_profit: float        # gross_profit - daily_expenses - monthly_expenses - salaries
    credit_outstanding: float = 0.0
    credit_received: float = 0.0

    # Sub-totals
    monthly_expenses: List[MonthlyExpenseResponse]
    salaries: List[EmployeeSalaryResponse]


class MonthlyCloseResponse(BaseModel):
    month: int
    year: int
    status: str
    total_sales: float
    total_purchase_cost: float
    total_daily_expenses: float
    total_monthly_expenses: float
    total_salaries: float
    net_profit: float
