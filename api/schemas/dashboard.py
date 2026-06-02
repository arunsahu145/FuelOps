"""Pydantic schemas for dashboard smart cards."""
from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class DashboardData(BaseModel):
    """Aggregated data for all dashboard smart cards."""
    # Sales Card
    today_total_sales: float = 0.0
    today_litres_sold: float = 0.0
    today_sales_by_fuel: List[dict] = []

    # Profit Card
    today_estimated_profit: float = 0.0

    # Expense Card
    today_total_expenses: float = 0.0

    # Purchases Card (replaces Tank Stock)
    today_total_purchases: float = 0.0
    today_litres_purchased: float = 0.0
    today_purchases_by_fuel: List[dict] = []

    # Payment Collection Card
    today_total_payments: float = 0.0
    today_payments_by_method: List[dict] = []
    cash_collection: float = 0.0
    expected_cash_collection: float = 0.0

    # Payment shortfall warning (negative = cash below expected cash collection)
    payment_shortfall: float = 0.0

    # Customer credit ledger
    total_credits_given_today: float = 0.0
    total_credits_outstanding: float = 0.0
    total_repayment_amount_done: float = 0.0
    overdue_customers: int = 0
