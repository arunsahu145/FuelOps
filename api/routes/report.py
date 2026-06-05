"""
FastAPI route — Reports & Closings
Daily/Monthly summaries, close operations, employee salaries, and monthly expenses.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import date, datetime

from database.engine import get_db
from database.models import (
    Sale, Expense, Payment, FuelType, FuelPurchase,
    FuelPurchaseRate, FuelSellingRate, ShiftReading,
    Nozzle, NozzleAssignment,
    DailyReport, DailyProfitReport,
    MonthlyReport, MonthlyProfitReport,
    MonthlyExpense, EmployeeSalary, Employee,
    CustomerCredit, CustomerRepayment
)
from api.schemas.report import (
    DailyReportSummary, DailyCloseResponse,
    FuelSalesBreakdown, NozzleSalesBreakdown,
    PaymentBreakdown, ExpenseBreakdown, SalaryBreakdown,
    MonthlyReportSummary, MonthlyCloseResponse,
    MonthlyFuelBreakdown,
    EmployeeSalaryEntry, EmployeeSalaryResponse,
    MonthlyExpenseEntry, MonthlyExpenseResponse,
)
from utils.helpers import get_month_range

router = APIRouter(prefix="/api/report", tags=["Reports & Closings"])


# ═══════════════════════════════════════════════════════════════════════════════
# DAILY REPORT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/daily/summary", response_model=DailyReportSummary)
def get_daily_summary(
    report_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Generate a dynamic daily report summary."""
    if report_date is None:
        report_date = date.today()

    # Check if already closed
    existing = db.query(DailyReport).filter_by(report_date=report_date).first()
    is_closed = existing.is_closed if existing else False

    # ── Sales ──
    sales = db.query(Sale).filter(Sale.sale_date == report_date).all()
    total_sales = sum(s.total_amount for s in sales)
    total_litres_sold = sum(s.litres_sold for s in sales)

    # Fuel breakdown
    fuel_groups = {}
    for s in sales:
        fuel = db.query(FuelType).filter_by(id=s.fuel_type_id).first()
        fname = fuel.name if fuel else "Unknown"
        if fname not in fuel_groups:
            # Get purchase rate — try configured rate first, then fall back to
            # the latest actual purchase transaction's price per litre
            pr = db.query(FuelPurchaseRate).filter(
                FuelPurchaseRate.fuel_type_id == s.fuel_type_id
            ).order_by(desc(FuelPurchaseRate.effective_from)).first()
            purchase_price = pr.price_per_litre if pr else 0.0

            # Fallback: if no configured rate, use latest purchase record
            if purchase_price == 0.0:
                latest_purchase = db.query(FuelPurchase).filter(
                    FuelPurchase.fuel_type_id == s.fuel_type_id
                ).order_by(desc(FuelPurchase.purchase_date)).first()
                if latest_purchase:
                    purchase_price = latest_purchase.price_per_litre

            fuel_groups[fname] = {
                "litres": 0.0, "sales": 0.0,
                "purchase_price": purchase_price,
                "selling_price": s.selling_price,
            }
        fuel_groups[fname]["litres"] += s.litres_sold
        fuel_groups[fname]["sales"] += s.total_amount

    fuel_breakdown = []
    total_purchase_cost = 0.0
    for fname, data in fuel_groups.items():
        cost = data["litres"] * data["purchase_price"]
        total_purchase_cost += cost
        profit = data["sales"] - cost
        fuel_breakdown.append(FuelSalesBreakdown(
            fuel_type=fname,
            litres_sold=data["litres"],
            sales_amount=data["sales"],
            purchase_cost_per_litre=data["purchase_price"],
            selling_price_per_litre=data["selling_price"],
            profit=profit,
        ))

    # Nozzle breakdown
    readings = db.query(ShiftReading).filter(
        ShiftReading.reading_date == report_date
    ).order_by(ShiftReading.shift_number, ShiftReading.nozzle_id).all()

    nozzle_breakdown = []
    for r in readings:
        nozzle = db.query(Nozzle).filter_by(id=r.nozzle_id).first()
        fuel = db.query(FuelType).filter_by(id=r.fuel_type_id).first()
        nozzle_breakdown.append(NozzleSalesBreakdown(
            nozzle_number=nozzle.nozzle_number if nozzle else 0,
            fuel_type=fuel.name if fuel else "Unknown",
            shift_number=r.shift_number,
            litres_sold=r.fuel_sold_litres,
            sales_amount=r.sales_amount,
        ))

    # ── Payments ──
    payments = db.query(Payment).filter(Payment.payment_date == report_date).all()

    # Separate commission from regular payments
    commission_total = sum(p.amount for p in payments if p.payment_method == "Commission")
    regular_payments = [p for p in payments if p.payment_method != "Commission"]
    total_payments = sum(p.amount for p in regular_payments)

    pay_methods = {"Cash": 0.0, "Paytm": 0.0, "PhonePe": 0.0, "CCMS": 0.0}
    for p in regular_payments:
        if p.payment_method in pay_methods:
            pay_methods[p.payment_method] += p.amount
        else:
            pay_methods[p.payment_method] = p.amount

    payment_breakdown = [
        PaymentBreakdown(method=k, amount=v) for k, v in pay_methods.items()
    ]
    # ── Expenses ──
    expenses = db.query(Expense).filter(Expense.expense_date == report_date).all()
    total_expenses = sum(e.amount for e in expenses)

    exp_cats = {}
    for e in expenses:
        if e.category not in exp_cats:
            exp_cats[e.category] = 0.0
        exp_cats[e.category] += e.amount

    expense_breakdown = [
        ExpenseBreakdown(category=k, amount=v) for k, v in exp_cats.items()
    ]

    # ── Profit ──
    salaries = db.query(EmployeeSalary).filter(
        EmployeeSalary.paid_date == report_date
    ).order_by(EmployeeSalary.paid_date, EmployeeSalary.employee_name).all()
    total_salaries = sum(s.monthly_salary for s in salaries)
    salary_breakdown = [
        SalaryBreakdown(
            employee_name=s.employee_name,
            amount=s.monthly_salary,
            paid_date=s.paid_date or report_date,
        ) for s in salaries
    ]
    cash_collection = pay_methods.get("Cash", 0.0)
    non_cash_collections = (
        pay_methods.get("Paytm", 0.0) +
        pay_methods.get("PhonePe", 0.0) +
        pay_methods.get("CCMS", 0.0)
    )
    expected_cash_collection = (
        total_sales - non_cash_collections - total_expenses - total_salaries
        + commission_total
    )
    payment_shortfall = cash_collection - expected_cash_collection

    gross_profit = total_sales - total_purchase_cost
    net_profit = gross_profit - total_expenses - total_salaries
    total_customer_credit = db.query(func.coalesce(func.sum(CustomerCredit.amount), 0.0)).scalar() or 0.0
    total_customer_repaid = db.query(func.coalesce(func.sum(CustomerRepayment.amount), 0.0)).scalar() or 0.0
    credit_outstanding = max(float(total_customer_credit) - float(total_customer_repaid), 0.0)
    credit_received = db.query(func.coalesce(func.sum(CustomerRepayment.amount), 0.0)).filter(
        CustomerRepayment.repayment_date == report_date
    ).scalar() or 0.0

    return DailyReportSummary(
        report_date=report_date,
        is_closed=is_closed,
        total_sales=total_sales,
        total_litres_sold=total_litres_sold,
        fuel_breakdown=fuel_breakdown,
        nozzle_breakdown=nozzle_breakdown,
        total_payments=total_payments,
        payment_breakdown=payment_breakdown,
        cash_collection=cash_collection,
        expected_cash_collection=expected_cash_collection,
        payment_shortfall=payment_shortfall,
        total_expenses=total_expenses,
        expense_breakdown=expense_breakdown,
        total_salaries=total_salaries,
        salary_breakdown=salary_breakdown,
        gross_profit=gross_profit,
        net_profit=net_profit,
        credit_outstanding=credit_outstanding,
        credit_received=float(credit_received),
    )


@router.post("/daily/close", response_model=DailyCloseResponse)
def close_daily_report(
    report_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Freeze/close the daily report for a given date."""
    if report_date is None:
        report_date = date.today()

    # Check if already closed
    existing = db.query(DailyReport).filter_by(report_date=report_date).first()
    if existing and existing.is_closed:
        raise HTTPException(status_code=400, detail="This day is already closed.")

    # Compute aggregates
    summary = get_daily_summary(report_date=report_date, db=db)

    if existing:
        existing.total_sales = summary.total_sales
        existing.total_expenses = summary.total_expenses
        existing.total_payments = summary.total_payments
        existing.total_litres_sold = summary.total_litres_sold
        existing.is_closed = True
    else:
        daily = DailyReport(
            report_date=report_date,
            total_sales=summary.total_sales,
            total_expenses=summary.total_expenses,
            total_payments=summary.total_payments,
            total_litres_sold=summary.total_litres_sold,
            is_closed=True,
        )
        db.add(daily)

    # Save daily profit report
    existing_profit = db.query(DailyProfitReport).filter_by(report_date=report_date).first()
    total_purchase_cost = sum(
        fb.litres_sold * fb.purchase_cost_per_litre for fb in summary.fuel_breakdown
    )
    if existing_profit:
        existing_profit.total_sales = summary.total_sales
        existing_profit.total_purchase_cost = total_purchase_cost
        existing_profit.total_expenses = summary.total_expenses
        existing_profit.gross_profit = summary.gross_profit
        existing_profit.net_profit = summary.net_profit
    else:
        profit_report = DailyProfitReport(
            report_date=report_date,
            total_sales=summary.total_sales,
            total_purchase_cost=total_purchase_cost,
            total_expenses=summary.total_expenses,
            gross_profit=summary.gross_profit,
            net_profit=summary.net_profit,
        )
        db.add(profit_report)

    db.commit()

    return DailyCloseResponse(
        report_date=report_date,
        status="closed",
        total_sales=summary.total_sales,
        total_expenses=summary.total_expenses,
        total_payments=summary.total_payments,
        net_profit=summary.net_profit,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MONTHLY REPORT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/monthly/summary", response_model=MonthlyReportSummary)
def get_monthly_summary(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db)
):
    """Generate a dynamic monthly report summary."""
    first_day, last_day = get_month_range(year, month)

    # Check if already closed
    existing = db.query(MonthlyReport).filter_by(month=month, year=year).first()
    is_closed = existing.is_closed if existing else False

    # ── Sales & Purchase Cost (COGS) ──
    sales = db.query(Sale).filter(
        Sale.sale_date >= first_day, Sale.sale_date <= last_day
    ).all()
    total_sales = sum(s.total_amount for s in sales)
    total_litres_sold = sum(s.litres_sold for s in sales)

    fuel_groups = {}
    for s in sales:
        fuel = db.query(FuelType).filter_by(id=s.fuel_type_id).first()
        fname = fuel.name if fuel else "Unknown"
        if fname not in fuel_groups:
            # Get purchase rate — try configured rate first, then fall back to
            # the latest actual purchase transaction's price per litre
            pr = db.query(FuelPurchaseRate).filter(
                FuelPurchaseRate.fuel_type_id == s.fuel_type_id
            ).order_by(desc(FuelPurchaseRate.effective_from)).first()
            purchase_price = pr.price_per_litre if pr else 0.0

            if purchase_price == 0.0:
                latest_purchase = db.query(FuelPurchase).filter(
                    FuelPurchase.fuel_type_id == s.fuel_type_id
                ).order_by(desc(FuelPurchase.purchase_date)).first()
                if latest_purchase:
                    purchase_price = latest_purchase.price_per_litre

            fuel_groups[fname] = {
                "litres": 0.0, "sales": 0.0,
                "purchase_price": purchase_price
            }
        fuel_groups[fname]["litres"] += s.litres_sold
        fuel_groups[fname]["sales"] += s.total_amount

    fuel_breakdown = []
    total_purchase_cost = 0.0
    for fname, data in fuel_groups.items():
        cost = data["litres"] * data["purchase_price"]
        total_purchase_cost += cost
        profit = data["sales"] - cost
        fuel_breakdown.append(MonthlyFuelBreakdown(
            fuel_type=fname,
            litres_sold=data["litres"],
            sales_amount=data["sales"],
            purchase_cost=cost,
            profit=profit,
        ))

    # ── Daily Expenses ──
    expenses = db.query(Expense).filter(
        Expense.expense_date >= first_day, Expense.expense_date <= last_day
    ).all()
    total_daily_expenses = sum(e.amount for e in expenses)

    # ── Monthly Expenses ──
    monthly_exps = db.query(MonthlyExpense).filter_by(month=month, year=year).all()
    total_monthly_expenses = sum(me.amount for me in monthly_exps)

    monthly_exp_responses = [
        MonthlyExpenseResponse(
            id=me.id, category=me.category, amount=me.amount,
            description=me.description, month=me.month, year=me.year,
        ) for me in monthly_exps
    ]

    # ── Salaries ──
    salaries = db.query(EmployeeSalary).filter_by(month=month, year=year).order_by(
        EmployeeSalary.paid_date, EmployeeSalary.employee_name
    ).all()
    total_salaries = sum(s.monthly_salary for s in salaries)

    salary_responses = [
        EmployeeSalaryResponse(
            id=s.id, employee_name=s.employee_name,
            designation=s.designation, monthly_salary=s.monthly_salary,
            month=s.month, year=s.year,
            is_paid=s.is_paid, paid_date=s.paid_date,
        ) for s in salaries
    ]

    # ── Payments ──
    payments = db.query(Payment).filter(
        Payment.payment_date >= first_day, Payment.payment_date <= last_day
    ).all()

    # Separate commission from regular payments
    commission_total = sum(p.amount for p in payments if p.payment_method == "Commission")
    regular_payments = [p for p in payments if p.payment_method != "Commission"]
    total_payments = sum(p.amount for p in regular_payments)

    pay_methods = {"Cash": 0.0, "Paytm": 0.0, "PhonePe": 0.0, "CCMS": 0.0}
    for p in regular_payments:
        if p.payment_method in pay_methods:
            pay_methods[p.payment_method] += p.amount
        else:
            pay_methods[p.payment_method] = p.amount
    payment_breakdown = [
        PaymentBreakdown(method=k, amount=v) for k, v in pay_methods.items()
    ]
    cash_collection = pay_methods.get("Cash", 0.0)
    non_cash_collections = (
        pay_methods.get("Paytm", 0.0) +
        pay_methods.get("PhonePe", 0.0) +
        pay_methods.get("CCMS", 0.0)
    )
    expected_cash_collection = (
        total_sales - non_cash_collections -
        total_daily_expenses - total_monthly_expenses - total_salaries
        + commission_total
    )
    payment_shortfall = cash_collection - expected_cash_collection

    # ── Profit ──
    gross_profit = total_sales - total_purchase_cost
    net_profit = gross_profit - total_daily_expenses - total_monthly_expenses - total_salaries
    total_customer_credit = db.query(func.coalesce(func.sum(CustomerCredit.amount), 0.0)).scalar() or 0.0
    total_customer_repaid = db.query(func.coalesce(func.sum(CustomerRepayment.amount), 0.0)).scalar() or 0.0
    credit_outstanding = max(float(total_customer_credit) - float(total_customer_repaid), 0.0)
    credit_received = db.query(func.coalesce(func.sum(CustomerRepayment.amount), 0.0)).filter(
        CustomerRepayment.repayment_date >= first_day,
        CustomerRepayment.repayment_date <= last_day,
    ).scalar() or 0.0

    # ── Actual Fuel Purchases ──
    actual_purchases = db.query(FuelPurchase).filter(
        FuelPurchase.purchase_date >= first_day,
        FuelPurchase.purchase_date <= last_day
    ).all()
    total_actual_purchases = float(sum(p.total_cost for p in actual_purchases))
    total_actual_litres_purchased = float(sum(p.litres_purchased for p in actual_purchases))

    return MonthlyReportSummary(
        month=month, year=year, is_closed=is_closed,
        total_sales=total_sales,
        total_litres_sold=total_litres_sold,
        fuel_breakdown=fuel_breakdown,
        total_purchase_cost=total_purchase_cost,
        total_actual_purchases=total_actual_purchases,
        total_actual_litres_purchased=total_actual_litres_purchased,
        total_payments=total_payments,
        payment_breakdown=payment_breakdown,
        cash_collection=cash_collection,
        expected_cash_collection=expected_cash_collection,
        payment_shortfall=payment_shortfall,
        total_daily_expenses=total_daily_expenses,
        total_monthly_expenses=total_monthly_expenses,
        total_salaries=total_salaries,
        gross_profit=gross_profit,
        net_profit=net_profit,
        credit_outstanding=credit_outstanding,
        credit_received=float(credit_received),
        monthly_expenses=monthly_exp_responses,
        salaries=salary_responses,
    )


@router.post("/monthly/close", response_model=MonthlyCloseResponse)
def close_monthly_report(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db)
):
    """Freeze/close the monthly report."""
    existing = db.query(MonthlyReport).filter_by(month=month, year=year).first()
    if existing and existing.is_closed:
        raise HTTPException(status_code=400, detail="This month is already closed.")

    summary = get_monthly_summary(year=year, month=month, db=db)

    if existing:
        existing.total_sales = summary.total_sales
        existing.total_purchases = summary.total_purchase_cost
        existing.total_expenses = summary.total_daily_expenses + summary.total_monthly_expenses
        existing.total_salaries = summary.total_salaries
        existing.net_profit = summary.net_profit
        existing.is_closed = True
    else:
        report = MonthlyReport(
            month=month, year=year,
            total_sales=summary.total_sales,
            total_purchases=summary.total_purchase_cost,
            total_expenses=summary.total_daily_expenses + summary.total_monthly_expenses,
            total_salaries=summary.total_salaries,
            net_profit=summary.net_profit,
            is_closed=True,
        )
        db.add(report)

    # Save monthly profit report
    existing_profit = db.query(MonthlyProfitReport).filter_by(month=month, year=year).first()
    if existing_profit:
        existing_profit.total_sales = summary.total_sales
        existing_profit.total_purchase_cost = summary.total_purchase_cost
        existing_profit.total_daily_expenses = summary.total_daily_expenses
        existing_profit.total_monthly_expenses = summary.total_monthly_expenses
        existing_profit.total_salaries = summary.total_salaries
        existing_profit.net_profit = summary.net_profit
    else:
        profit_report = MonthlyProfitReport(
            month=month, year=year,
            total_sales=summary.total_sales,
            total_purchase_cost=summary.total_purchase_cost,
            total_daily_expenses=summary.total_daily_expenses,
            total_monthly_expenses=summary.total_monthly_expenses,
            total_salaries=summary.total_salaries,
            net_profit=summary.net_profit,
        )
        db.add(profit_report)

    db.commit()

    return MonthlyCloseResponse(
        month=month, year=year, status="closed",
        total_sales=summary.total_sales,
        total_purchase_cost=summary.total_purchase_cost,
        total_daily_expenses=summary.total_daily_expenses,
        total_monthly_expenses=summary.total_monthly_expenses,
        total_salaries=summary.total_salaries,
        net_profit=summary.net_profit,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE SALARIES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/salaries", response_model=List[EmployeeSalaryResponse])
def get_salaries(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get all employee salary records for a given month/year."""
    salaries = db.query(EmployeeSalary).filter_by(month=month, year=year).order_by(
        EmployeeSalary.paid_date, EmployeeSalary.employee_name
    ).all()
    return [
        EmployeeSalaryResponse(
            id=s.id, employee_name=s.employee_name,
            designation=s.designation, monthly_salary=s.monthly_salary,
            month=s.month, year=s.year,
            is_paid=s.is_paid, paid_date=s.paid_date,
        ) for s in salaries
    ]


@router.post("/salaries", response_model=EmployeeSalaryResponse)
def add_salary(
    entry: EmployeeSalaryEntry,
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db)
):
    """Add an employee salary record for a given month/year."""
    paid_date = entry.paid_date or date(year, month, 1)
    salary = EmployeeSalary(
        employee_name=entry.employee_name,
        designation=entry.designation,
        monthly_salary=entry.monthly_salary,
        month=month, year=year,
        is_paid=True,
        paid_date=paid_date,
    )
    db.add(salary)
    db.commit()
    db.refresh(salary)

    return EmployeeSalaryResponse(
        id=salary.id, employee_name=salary.employee_name,
        designation=salary.designation, monthly_salary=salary.monthly_salary,
        month=salary.month, year=salary.year,
        is_paid=salary.is_paid, paid_date=salary.paid_date,
    )


@router.delete("/salaries/{salary_id}")
def delete_salary(salary_id: int, db: Session = Depends(get_db)):
    """Delete an employee salary record."""
    salary = db.query(EmployeeSalary).filter_by(id=salary_id).first()
    if not salary:
        raise HTTPException(status_code=404, detail="Salary record not found")
    db.delete(salary)
    db.commit()
    return {"detail": "Salary record deleted", "id": salary_id}


@router.post("/salaries/{salary_id}/mark-paid")
def mark_salary_paid(salary_id: int, db: Session = Depends(get_db)):
    """Mark a salary record as paid."""
    salary = db.query(EmployeeSalary).filter_by(id=salary_id).first()
    if not salary:
        raise HTTPException(status_code=404, detail="Salary record not found")
    salary.is_paid = True
    salary.paid_date = date.today()
    db.commit()
    return {"detail": "Salary marked as paid", "id": salary_id}


# ═══════════════════════════════════════════════════════════════════════════════
# MONTHLY EXPENSES (rent, electricity bills, etc.)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/monthly-expenses", response_model=List[MonthlyExpenseResponse])
def get_monthly_expenses(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get all monthly expense records for a given month/year."""
    expenses = db.query(MonthlyExpense).filter_by(month=month, year=year).all()
    return [
        MonthlyExpenseResponse(
            id=me.id, category=me.category, amount=me.amount,
            description=me.description, month=me.month, year=me.year,
        ) for me in expenses
    ]


@router.post("/monthly-expenses", response_model=MonthlyExpenseResponse)
def add_monthly_expense(
    entry: MonthlyExpenseEntry,
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db)
):
    """Add a monthly expense record (rent, electricity, etc.)."""
    expense = MonthlyExpense(
        category=entry.category,
        amount=entry.amount,
        description=entry.description,
        month=month, year=year,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    return MonthlyExpenseResponse(
        id=expense.id, category=expense.category, amount=expense.amount,
        description=expense.description, month=expense.month, year=expense.year,
    )


@router.delete("/monthly-expenses/{expense_id}")
def delete_monthly_expense(expense_id: int, db: Session = Depends(get_db)):
    """Delete a monthly expense record."""
    expense = db.query(MonthlyExpense).filter_by(id=expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Monthly expense not found")
    db.delete(expense)
    db.commit()
    return {"detail": "Monthly expense deleted", "id": expense_id}


# ═══════════════════════════════════════════════════════════════════════════════
# LOAD SALARIES FROM EMPLOYEE MASTER
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/salaries/load-from-employees")
def load_salaries_from_employees(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db)
):
    """Disabled: salaries are now recorded as dated payments from employees."""
    raise HTTPException(
        status_code=410,
        detail="Monthly salary loading has been removed. Pay salary from the employee list.",
    )
