"""
Petrol Pump Finance Manager ERP — Configuration
"""
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "petrol_pump.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ── Embedded API ─────────────────────────────────────────────────────────
API_HOST = "127.0.0.1"
API_PORT = 8321
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

# ── Auth ─────────────────────────────────────────────────────────────────
SECRET_KEY = "petrol-pump-erp-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8-hour session

# ── Default Admin ────────────────────────────────────────────────────────
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

# ── Fuel Configuration ───────────────────────────────────────────────────
FUEL_TYPES = ["Petrol", "Power Petrol", "Diesel"]
TOTAL_NOZZLES = 8

# ── Fuel Type Colors ─────────────────────────────────────────────────────
FUEL_COLORS = {
    "Petrol": "#10b981",        # Emerald
    "Power Petrol": "#0ea5e9",  # Sky blue
    "Diesel": "#f59e0b",        # Amber
}

# ── Expense Categories ───────────────────────────────────────────────────
EXPENSE_CATEGORIES = [
    "Electricity", "Water", "Maintenance",
    "Repairs", "Miscellaneous", "Extra"
]

# ── Payment Methods ──────────────────────────────────────────────────────
PAYMENT_METHODS = ["Cash", "Paytm", "PhonePe", "CCMS"]

# ── Currency ─────────────────────────────────────────────────────────────
CURRENCY_SYMBOL = "₹"
