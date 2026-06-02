"""
Petrol Pump Finance Manager ERP — Utility Helpers
Currency formatting, date utilities, and common helper functions.
"""
from datetime import datetime, date, timedelta
from typing import Optional
import locale


def format_currency(amount: float) -> str:
    """
    Format a number as Indian Rupees with proper comma grouping.
    Example: 123456.78 → ₹1,23,456.78
    """
    if amount is None:
        return "₹0.00"

    is_negative = amount < 0
    amount = abs(amount)

    # Split into integer and decimal parts
    int_part = int(amount)
    dec_part = f"{amount - int_part:.2f}"[1:]  # ".XX"

    # Indian comma grouping: last 3 digits, then groups of 2
    s = str(int_part)
    if len(s) <= 3:
        formatted = s
    else:
        # Last 3 digits
        last3 = s[-3:]
        remaining = s[:-3]
        # Group remaining in pairs from right
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        groups.reverse()
        formatted = ",".join(groups) + "," + last3

    result = f"₹{formatted}{dec_part}"
    if is_negative:
        result = f"-{result}"
    return result


def format_litres(litres: float) -> str:
    """Format litres with 2 decimal places and 'L' suffix."""
    if litres is None:
        return "0.00 L"
    return f"{litres:,.2f} L"


def format_date(d: Optional[date] = None) -> str:
    """Format date as DD-MM-YYYY (Indian standard)."""
    if d is None:
        d = date.today()
    return d.strftime("%d-%m-%Y")


def format_datetime(dt: Optional[datetime] = None) -> str:
    """Format datetime as DD-MM-YYYY HH:MM."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%d-%m-%Y %H:%M")


def parse_date(date_str: str) -> date:
    """Parse a date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def get_today() -> date:
    """Get today's date."""
    return date.today()


def get_month_range(year: int, month: int) -> tuple:
    """Get the first and last date of a given month."""
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    return first_day, last_day


def get_month_name(month: int) -> str:
    """Get month name from month number."""
    months = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    return months[month] if 1 <= month <= 12 else ""


# ─── Fuel Type Color Mapping ─────────────────────────────────────────────────
FUEL_COLORS = {
    "Petrol": "#10b981",        # Emerald green
    "Power Petrol": "#0ea5e9",  # Sky blue
    "Diesel": "#f59e0b",        # Amber
}

def get_fuel_color(fuel_type: str) -> str:
    """Get the theme color for a fuel type."""
    return FUEL_COLORS.get(fuel_type, "#94a3b8")  # Default: slate-400
