"""
Petrol Pump Finance Manager ERP — Database Models
All SQLAlchemy ORM models for the 20+ database tables.
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime,
    ForeignKey, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from database.engine import Base


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN / AUTH
# ═══════════════════════════════════════════════════════════════════════════════

class AdminUser(Base):
    """Single admin user for the system."""
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False, default="Administrator")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FUEL MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class FuelType(Base):
    """Fuel types managed in the system (Petrol, Power Petrol, Diesel)."""
    __tablename__ = "fuel_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    purchase_rates = relationship("FuelPurchaseRate", back_populates="fuel_type")
    selling_rates = relationship("FuelSellingRate", back_populates="fuel_type")
    nozzle_assignments = relationship("NozzleAssignment", back_populates="fuel_type")
    purchases = relationship("FuelPurchase", back_populates="fuel_type")
    tank_stocks = relationship("TankStock", back_populates="fuel_type")


class FuelPurchaseRate(Base):
    """Purchase price history per fuel type (price per litre)."""
    __tablename__ = "fuel_purchase_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fuel_type_id = Column(Integer, ForeignKey("fuel_types.id"), nullable=False)
    price_per_litre = Column(Float, nullable=False)
    effective_from = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    fuel_type = relationship("FuelType", back_populates="purchase_rates")


class FuelSellingRate(Base):
    """Selling price history per fuel type (price per litre)."""
    __tablename__ = "fuel_selling_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fuel_type_id = Column(Integer, ForeignKey("fuel_types.id"), nullable=False)
    price_per_litre = Column(Float, nullable=False)
    effective_from = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    fuel_type = relationship("FuelType", back_populates="selling_rates")


# ═══════════════════════════════════════════════════════════════════════════════
# NOZZLE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class Nozzle(Base):
    """Physical nozzles at the petrol pump (8 total)."""
    __tablename__ = "nozzles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nozzle_number = Column(Integer, unique=True, nullable=False)
    label = Column(String(50), nullable=True)  # e.g., "Nozzle 1"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    assignments = relationship("NozzleAssignment", back_populates="nozzle")
    shift_readings = relationship("ShiftReading", back_populates="nozzle")


class NozzleAssignment(Base):
    """Maps each nozzle to a fuel type. One active assignment per nozzle."""
    __tablename__ = "nozzle_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nozzle_id = Column(Integer, ForeignKey("nozzles.id"), nullable=False)
    fuel_type_id = Column(Integer, ForeignKey("fuel_types.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)

    nozzle = relationship("Nozzle", back_populates="assignments")
    fuel_type = relationship("FuelType", back_populates="nozzle_assignments")

    __table_args__ = (
        # Only one active assignment per nozzle at a time
        Index("ix_active_nozzle_assignment", "nozzle_id", "is_active"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SHIFT & SALES
# ═══════════════════════════════════════════════════════════════════════════════

class ShiftReading(Base):
    """Meter readings per nozzle per shift per day."""
    __tablename__ = "shift_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nozzle_id = Column(Integer, ForeignKey("nozzles.id"), nullable=False)
    shift_number = Column(Integer, nullable=False)  # 1 or 2
    reading_date = Column(Date, nullable=False)
    opening_reading = Column(Float, nullable=False)
    closing_reading = Column(Float, nullable=False)
    fuel_sold_litres = Column(Float, nullable=False)  # closing - opening
    fuel_type_id = Column(Integer, ForeignKey("fuel_types.id"), nullable=False)
    selling_price_per_litre = Column(Float, nullable=False)  # Price at time of reading
    sales_amount = Column(Float, nullable=False)  # fuel_sold × selling_price
    created_at = Column(DateTime, default=datetime.now)

    nozzle = relationship("Nozzle", back_populates="shift_readings")
    fuel_type = relationship("FuelType")

    __table_args__ = (
        # One reading per nozzle per shift per day
        UniqueConstraint("nozzle_id", "shift_number", "reading_date",
                         name="uq_nozzle_shift_date"),
    )


class Sale(Base):
    """Aggregated sales records derived from shift readings."""
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_date = Column(Date, nullable=False, index=True)
    fuel_type_id = Column(Integer, ForeignKey("fuel_types.id"), nullable=False)
    nozzle_id = Column(Integer, ForeignKey("nozzles.id"), nullable=True)
    shift_number = Column(Integer, nullable=True)
    litres_sold = Column(Float, nullable=False, default=0.0)
    selling_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)
    shift_reading_id = Column(Integer, ForeignKey("shift_readings.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    fuel_type = relationship("FuelType")
    nozzle = relationship("Nozzle")


class SalesAnalytics(Base):
    """Pre-computed sales analytics for fast dashboard queries (Phase 3)."""
    __tablename__ = "sales_analytics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analytics_date = Column(Date, nullable=False)
    fuel_type_id = Column(Integer, ForeignKey("fuel_types.id"), nullable=True)
    period_type = Column(String(20), nullable=False)  # 'daily', 'monthly', 'yearly'
    total_litres = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    avg_price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)


# ═══════════════════════════════════════════════════════════════════════════════
# PURCHASES
# ═══════════════════════════════════════════════════════════════════════════════

class FuelPurchase(Base):
    """Records of fuel purchased from suppliers."""
    __tablename__ = "fuel_purchases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fuel_type_id = Column(Integer, ForeignKey("fuel_types.id"), nullable=False)
    purchase_date = Column(Date, nullable=False, index=True)
    litres_purchased = Column(Float, nullable=False)
    price_per_litre = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    supplier_name = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    fuel_type = relationship("FuelType", back_populates="purchases")


# ═══════════════════════════════════════════════════════════════════════════════
# TANK STOCK
# ═══════════════════════════════════════════════════════════════════════════════

class TankStock(Base):
    """Current tank stock per fuel type. One row per fuel type."""
    __tablename__ = "tank_stock"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fuel_type_id = Column(Integer, ForeignKey("fuel_types.id"), unique=True, nullable=False)
    current_stock_litres = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    fuel_type = relationship("FuelType", back_populates="tank_stocks")


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENTS
# ═══════════════════════════════════════════════════════════════════════════════

class Payment(Base):
    """Payment collections (Cash, Paytm, PhonePe, CCMS) per shift."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_date = Column(Date, nullable=False, index=True)
    shift_number = Column(Integer, nullable=True)  # 1 or 2
    payment_method = Column(String(50), nullable=False)  # Cash, Paytm, PhonePe, CCMS
    amount = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPENSES
# ═══════════════════════════════════════════════════════════════════════════════

class Customer(Base):
    """Customer master register for credit customers."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_code = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    credits = relationship("CustomerCredit", back_populates="customer")
    repayments = relationship("CustomerRepayment", back_populates="customer")


class CustomerCredit(Base):
    """Append-only customer credit entries."""
    __tablename__ = "customer_credits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    credit_date = Column(Date, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=True, index=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    customer = relationship("Customer", back_populates="credits")


class CustomerRepayment(Base):
    """Append-only customer repayment history."""
    __tablename__ = "customer_repayments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    repayment_date = Column(Date, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    mode = Column(String(50), nullable=False)
    reference_number = Column(String(100), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    customer = relationship("Customer", back_populates="repayments")


class Expense(Base):
    """Daily operational expenses."""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    expense_date = Column(Date, nullable=False, index=True)
    category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class Employee(Base):
    """Master employee register — permanent employee details."""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=True)
    phone = Column(String(15), nullable=True)
    monthly_salary = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class MonthlyExpense(Base):
    """Monthly recurring expenses (rent, salaries, etc.)."""
    __tablename__ = "monthly_expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)
    category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class EmployeeSalary(Base):
    """Employee salary records for monthly deduction."""
    __tablename__ = "employee_salaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_name = Column(String(100), nullable=False)
    designation = Column(String(100), nullable=True)
    monthly_salary = Column(Float, nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    is_paid = Column(Boolean, default=False)
    paid_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTS (Phase 2 — Tables defined now)
# ═══════════════════════════════════════════════════════════════════════════════

class DailyReport(Base):
    """End-of-day closing report."""
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Date, unique=True, nullable=False)
    total_sales = Column(Float, default=0.0)
    total_expenses = Column(Float, default=0.0)
    total_payments = Column(Float, default=0.0)
    total_litres_sold = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


class MonthlyReport(Base):
    """Monthly summary report."""
    __tablename__ = "monthly_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    total_sales = Column(Float, default=0.0)
    total_purchases = Column(Float, default=0.0)
    total_expenses = Column(Float, default=0.0)
    total_salaries = Column(Float, default=0.0)
    net_profit = Column(Float, default=0.0)
    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("month", "year", name="uq_monthly_report"),
    )


class DailyProfitReport(Base):
    """Daily profit breakdown."""
    __tablename__ = "daily_profit_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Date, unique=True, nullable=False)
    total_sales = Column(Float, default=0.0)
    total_purchase_cost = Column(Float, default=0.0)
    total_expenses = Column(Float, default=0.0)
    gross_profit = Column(Float, default=0.0)
    net_profit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)


class MonthlyProfitReport(Base):
    """Monthly profit breakdown."""
    __tablename__ = "monthly_profit_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    total_sales = Column(Float, default=0.0)
    total_purchase_cost = Column(Float, default=0.0)
    total_daily_expenses = Column(Float, default=0.0)
    total_monthly_expenses = Column(Float, default=0.0)
    total_salaries = Column(Float, default=0.0)
    net_profit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("month", "year", name="uq_monthly_profit_report"),
    )


class ProfitReport(Base):
    """General profit/loss report entries."""
    __tablename__ = "profit_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(20), nullable=False)  # 'daily' or 'monthly'
    report_date = Column(Date, nullable=True)
    month = Column(Integer, nullable=True)
    year = Column(Integer, nullable=True)
    revenue = Column(Float, default=0.0)
    cost = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)


# ═══════════════════════════════════════════════════════════════════════════════
# BANK DEPOSITS
# ═══════════════════════════════════════════════════════════════════════════════

class BankDeposit(Base):
    """Monthly bank deposit records (Working Capital, Solar, Truck, Top Up Finance)."""
    __tablename__ = "bank_deposits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    deposit_date = Column(Date, nullable=True)
    working_capital = Column(Float, default=0.0)
    solar = Column(Float, default=0.0)
    truck = Column(Float, default=0.0)
    top_up_finance = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

