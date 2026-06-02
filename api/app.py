"""
Petrol Pump Finance Manager ERP — FastAPI Application
Creates and configures the FastAPI app instance.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.engine import init_db
from database.seed import run_seed


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Petrol Pump Finance Manager ERP",
        version="1.0.0",
        description="Backend API for Petrol Pump ERP System",
    )

    # CORS middleware (for local development)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and include all route modules
    from api.routes import auth, fuel, nozzle, shift, sales, purchase, payment, expense, dashboard, report, employee, alerts, backup, credit
    app.include_router(auth.router, tags=["Auth"])
    app.include_router(fuel.router, tags=["Fuel"])
    app.include_router(nozzle.router, tags=["Nozzle"])
    app.include_router(shift.router, tags=["Shift"])
    app.include_router(sales.router, tags=["Sales"])
    app.include_router(purchase.router, tags=["Purchase"])
    app.include_router(payment.router, tags=["Payment"])
    app.include_router(credit.router, tags=["Customer Credit"])
    app.include_router(expense.router, tags=["Expense"])
    app.include_router(dashboard.router, tags=["Dashboard"])
    app.include_router(report.router, tags=["Reports"])
    app.include_router(employee.router, tags=["Employees"])
    app.include_router(alerts.router, tags=["Alerts"])
    app.include_router(backup.router, tags=["Backup"])

    @app.on_event("startup")
    def startup():
        """Initialize database, seed data, and auto-close stale periods on startup."""
        init_db()
        run_seed()
        _auto_close_previous_month()

    @app.get("/health")
    def health_check():
        return {"status": "healthy", "app": "Petrol Pump ERP"}

    return app


def _auto_close_previous_month():
    """Auto-close the previous month's report if it's still open."""
    from datetime import date
    from database.engine import SessionLocal
    from database.models import (
        MonthlyReport, MonthlyProfitReport, Sale, FuelPurchase,
        Expense, MonthlyExpense, EmployeeSalary, Payment
    )
    from utils.helpers import get_month_range

    today = date.today()
    if today.day < 2:
        return  # Only auto-close once we're at least on the 2nd

    # Previous month
    if today.month == 1:
        prev_month, prev_year = 12, today.year - 1
    else:
        prev_month, prev_year = today.month - 1, today.year

    db = SessionLocal()
    try:
        existing = db.query(MonthlyReport).filter_by(month=prev_month, year=prev_year).first()
        if existing and existing.is_closed:
            return  # Already closed

        first_day, last_day = get_month_range(prev_year, prev_month)

        # Aggregate data
        sales = db.query(Sale).filter(
            Sale.sale_date >= first_day, Sale.sale_date <= last_day
        ).all()
        total_sales = sum(s.total_amount for s in sales)

        from sqlalchemy import desc
        from database.models import FuelPurchaseRate

        # Calculate purchase cost based on sales and purchase rates (COGS)
        total_purchase_cost = 0.0
        fuel_purchase_prices = {}
        for s in sales:
            if s.fuel_type_id not in fuel_purchase_prices:
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
                fuel_purchase_prices[s.fuel_type_id] = purchase_price

            total_purchase_cost += s.litres_sold * fuel_purchase_prices[s.fuel_type_id]

        expenses = db.query(Expense).filter(
            Expense.expense_date >= first_day, Expense.expense_date <= last_day
        ).all()
        total_daily_expenses = sum(e.amount for e in expenses)

        monthly_exps = db.query(MonthlyExpense).filter_by(
            month=prev_month, year=prev_year
        ).all()
        total_monthly_expenses = sum(me.amount for me in monthly_exps)

        salaries = db.query(EmployeeSalary).filter_by(
            month=prev_month, year=prev_year
        ).all()
        total_salaries = sum(s.monthly_salary for s in salaries)

        gross_profit = total_sales - total_purchase_cost
        net_profit = gross_profit - total_daily_expenses - total_monthly_expenses - total_salaries

        if existing:
            existing.total_sales = total_sales
            existing.total_purchases = total_purchase_cost
            existing.total_expenses = total_daily_expenses + total_monthly_expenses
            existing.total_salaries = total_salaries
            existing.net_profit = net_profit
            existing.is_closed = True
        else:
            report = MonthlyReport(
                month=prev_month, year=prev_year,
                total_sales=total_sales,
                total_purchases=total_purchase_cost,
                total_expenses=total_daily_expenses + total_monthly_expenses,
                total_salaries=total_salaries,
                net_profit=net_profit,
                is_closed=True,
            )
            db.add(report)

        # Save profit report
        existing_profit = db.query(MonthlyProfitReport).filter_by(
            month=prev_month, year=prev_year
        ).first()
        if existing_profit:
            existing_profit.total_sales = total_sales
            existing_profit.total_purchase_cost = total_purchase_cost
            existing_profit.total_daily_expenses = total_daily_expenses
            existing_profit.total_monthly_expenses = total_monthly_expenses
            existing_profit.total_salaries = total_salaries
            existing_profit.net_profit = net_profit
        else:
            profit_report = MonthlyProfitReport(
                month=prev_month, year=prev_year,
                total_sales=total_sales,
                total_purchase_cost=total_purchase_cost,
                total_daily_expenses=total_daily_expenses,
                total_monthly_expenses=total_monthly_expenses,
                total_salaries=total_salaries,
                net_profit=net_profit,
            )
            db.add(profit_report)

        db.commit()
        print(f"[AUTO-CLOSE] Month {prev_month}/{prev_year} auto-closed. Net profit: {net_profit:.2f}")
    except Exception as e:
        print(f"[AUTO-CLOSE] Warning: monthly auto-close failed: {e}")
    finally:
        db.close()
