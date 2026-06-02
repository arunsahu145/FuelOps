"""
FastAPI route — Dashboard Aggregations
Provides real-time stats for dashboard smart cards.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import date

from database.engine import get_db
from database.models import (
    Sale, Expense, Payment, FuelType, FuelPurchase, FuelPurchaseRate,
    FuelSellingRate, Customer, CustomerCredit, CustomerRepayment
)
from api.schemas.dashboard import DashboardData

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardData)
def get_dashboard_summary(
    dashboard_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Get aggregated data for all dashboard smart cards.
    """
    if dashboard_date is None:
        dashboard_date = date.today()

    # 1. SALES CARD INFO
    sales = db.query(Sale).filter(Sale.sale_date == dashboard_date).all()
    today_total_sales = sum(s.total_amount for s in sales)
    today_litres_sold = sum(s.litres_sold for s in sales)

    # Breakdown by fuel
    fuel_groups = {}
    for s in sales:
        fuel = db.query(FuelType).filter_by(id=s.fuel_type_id).first()
        fname = fuel.name if fuel else "Unknown"
        if fname not in fuel_groups:
            fuel_groups[fname] = 0.0
        fuel_groups[fname] += s.total_amount
    today_sales_by_fuel = [{"fuel_type": k, "amount": v} for k, v in fuel_groups.items()]

    # 2. PROFIT CARD INFO
    # Profit = (selling_price - purchase_price) * litres_sold
    today_estimated_profit = 0.0
    for s in sales:
        # Get purchase price at that time (latest purchase rate)
        purchase_rate = db.query(FuelPurchaseRate).filter(
            FuelPurchaseRate.fuel_type_id == s.fuel_type_id
        ).order_by(desc(FuelPurchaseRate.effective_from)).first()

        purchase_price = purchase_rate.price_per_litre if purchase_rate else 0.0
        profit_per_litre = s.selling_price - purchase_price
        today_estimated_profit += s.litres_sold * profit_per_litre

    # 3. EXPENSE CARD INFO
    expenses = db.query(Expense).filter(Expense.expense_date == dashboard_date).all()
    today_total_expenses = sum(e.amount for e in expenses)

    # 4. PURCHASES CARD INFO (replaces tank stock)
    purchases = db.query(FuelPurchase).filter(FuelPurchase.purchase_date == dashboard_date).all()
    today_total_purchases = sum(p.total_cost for p in purchases)
    today_litres_purchased = sum(p.litres_purchased for p in purchases)

    # Breakdown by fuel
    purchase_fuel_groups = {}
    for p in purchases:
        fuel = db.query(FuelType).filter_by(id=p.fuel_type_id).first()
        fname = fuel.name if fuel else "Unknown"
        if fname not in purchase_fuel_groups:
            purchase_fuel_groups[fname] = {"cost": 0.0, "litres": 0.0}
        purchase_fuel_groups[fname]["cost"] += p.total_cost
        purchase_fuel_groups[fname]["litres"] += p.litres_purchased
    today_purchases_by_fuel = [
        {"fuel_type": k, "cost": v["cost"], "litres": v["litres"]}
        for k, v in purchase_fuel_groups.items()
    ]

    # 5. PAYMENT COLLECTION CARD INFO
    payments = db.query(Payment).filter(Payment.payment_date == dashboard_date).all()
    today_total_payments = sum(p.amount for p in payments)

    # Payments by method — include CCMS
    pay_methods = {"Cash": 0.0, "Paytm": 0.0, "PhonePe": 0.0, "CCMS": 0.0}
    for p in payments:
        if p.payment_method in pay_methods:
            pay_methods[p.payment_method] += p.amount
        else:
            # Handle any unknown method gracefully
            pay_methods[p.payment_method] = p.amount
    today_payments_by_method = [{"method": k, "amount": v} for k, v in pay_methods.items()]

    # 6. PAYMENT SHORTFALL CHECK
    # Positive = excess collection, Negative = under-collected vs sales
    payment_shortfall = today_total_payments - today_total_sales

    # 7. CUSTOMER CREDIT INFO
    today_credit_rows = db.query(CustomerCredit).filter(
        CustomerCredit.credit_date == dashboard_date
    ).all()
    today_repayment_rows = db.query(CustomerRepayment).filter(
        CustomerRepayment.repayment_date == dashboard_date
    ).all()
    total_credit_all = db.query(CustomerCredit).all()
    total_repay_all = db.query(CustomerRepayment).all()
    total_credits_given_today = sum(c.amount for c in today_credit_rows)
    total_repayment_amount_done = sum(r.amount for r in today_repayment_rows)
    total_credits_outstanding = max(
        sum(c.amount for c in total_credit_all) - sum(r.amount for r in total_repay_all),
        0.0
    )

    overdue_customers = 0
    for customer in db.query(Customer).filter(Customer.is_active == True).all():
        credit_total = sum(c.amount for c in customer.credits)
        repayment_total = sum(r.amount for r in customer.repayments)
        if credit_total <= repayment_total:
            continue
        paid = repayment_total
        oldest_unpaid = None
        for credit in sorted(customer.credits, key=lambda item: (item.credit_date, item.id)):
            if paid >= credit.amount:
                paid -= credit.amount
                continue
            oldest_unpaid = credit.due_date or credit.credit_date
            break
        if oldest_unpaid and (dashboard_date - oldest_unpaid).days > 30:
            overdue_customers += 1

    return DashboardData(
        today_total_sales=today_total_sales,
        today_litres_sold=today_litres_sold,
        today_sales_by_fuel=today_sales_by_fuel,
        today_estimated_profit=today_estimated_profit,
        today_total_expenses=today_total_expenses,
        today_total_purchases=today_total_purchases,
        today_litres_purchased=today_litres_purchased,
        today_purchases_by_fuel=today_purchases_by_fuel,
        today_total_payments=today_total_payments,
        today_payments_by_method=today_payments_by_method,
        payment_shortfall=payment_shortfall,
        total_credits_given_today=total_credits_given_today,
        total_credits_outstanding=total_credits_outstanding,
        total_repayment_amount_done=total_repayment_amount_done,
        overdue_customers=overdue_customers
    )
