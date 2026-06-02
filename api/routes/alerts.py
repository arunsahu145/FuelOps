"""
Petrol Pump Finance Manager ERP — Alerts API
Runs 5 intelligent detectors against the database to surface anomalies.
"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.engine import get_db
from database.models import ShiftReading, Sale, Payment, Expense, Nozzle

router = APIRouter(prefix="/api/alerts")
DISMISSED_ALERT_IDS = set()


def _detect_nozzle_mismatch(db: Session, check_dates: list) -> list:
    """Detector 1: Closing reading < Opening reading for any shift reading."""
    alerts = []
    readings = db.query(ShiftReading).filter(
        ShiftReading.reading_date.in_(check_dates),
        ShiftReading.closing_reading < ShiftReading.opening_reading
    ).all()
    for r in readings:
        nozzle = db.query(Nozzle).filter_by(id=r.nozzle_id).first()
        nozzle_label = f"N{nozzle.nozzle_number}" if nozzle else f"Nozzle#{r.nozzle_id}"
        alerts.append({
            "id": f"nozzle_mismatch_{nozzle_label}_shift{r.shift_number}_{r.reading_date}",
            "severity": "critical",
            "title": f"Nozzle Mismatch — {nozzle_label} Shift {r.shift_number}",
            "message": f"Closing reading ({r.closing_reading:,.1f}) is less than opening reading ({r.opening_reading:,.1f}) on {r.reading_date}",
            "category": "nozzle_mismatch",
            "date": str(r.reading_date),
        })
    return alerts


def _detect_meter_mismatch(db: Session, check_dates: list) -> list:
    """Detector 2: Sum of shift fuel_sold_litres ≠ sum of Sale litres_sold (±1L tolerance)."""
    alerts = []
    for d in check_dates:
        shift_total = db.query(func.sum(ShiftReading.fuel_sold_litres)).filter(
            ShiftReading.reading_date == d
        ).scalar() or 0.0
        sale_total = db.query(func.sum(Sale.litres_sold)).filter(
            Sale.sale_date == d
        ).scalar() or 0.0

        # Only alert if both have data and mismatch exceeds tolerance
        if shift_total > 0 and sale_total > 0 and abs(shift_total - sale_total) > 1.0:
            diff = shift_total - sale_total
            alerts.append({
                "id": f"meter_mismatch_{d}",
                "severity": "warning",
                "title": f"Meter Mismatch — {d}",
                "message": f"Shift readings total ({shift_total:,.1f}L) differs from sales records ({sale_total:,.1f}L) by {abs(diff):,.1f}L",
                "category": "meter_mismatch",
                "date": str(d),
            })
    return alerts


def _detect_missing_shifts(db: Session, check_dates: list) -> list:
    """Detector 3: No shift readings recorded for today or yesterday."""
    alerts = []
    for d in check_dates:
        count = db.query(func.count(ShiftReading.id)).filter(
            ShiftReading.reading_date == d
        ).scalar() or 0
        if count == 0:
            day_label = "Today" if d == date.today() else "Yesterday"
            alerts.append({
                "id": f"missing_shifts_{d}",
                "severity": "warning",
                "title": f"Missing Shift Entries — {day_label}",
                "message": f"No shift readings have been recorded for {d}. Please enter meter readings.",
                "category": "missing_shifts",
                "date": str(d),
            })
    return alerts


def _detect_cash_mismatch(db: Session, today: date) -> list:
    """Detector 4: Cash payments deviate from (Total Sales - Digital payments) by > ₹100."""
    alerts = []
    total_sales = db.query(func.sum(Sale.total_amount)).filter(
        Sale.sale_date == today
    ).scalar() or 0.0

    if total_sales <= 0:
        return alerts

    cash_payments = db.query(func.sum(Payment.amount)).filter(
        Payment.payment_date == today,
        Payment.payment_method == "Cash"
    ).scalar() or 0.0

    digital_payments = db.query(func.sum(Payment.amount)).filter(
        Payment.payment_date == today,
        Payment.payment_method.in_(["Paytm", "PhonePe", "CCMS"])
    ).scalar() or 0.0

    expected_cash = total_sales - digital_payments
    diff = abs(cash_payments - expected_cash)

    if diff > 100 and (cash_payments > 0 or digital_payments > 0):
        alerts.append({
            "id": f"cash_mismatch_{today}",
            "severity": "warning",
            "title": "Cash Collection Mismatch — Today",
            "message": f"Cash collected (₹{cash_payments:,.0f}) differs from expected (₹{expected_cash:,.0f}) by ₹{diff:,.0f}",
            "category": "cash_mismatch",
            "date": str(today),
        })
    return alerts


def _detect_large_expenses(db: Session, today: date) -> list:
    """Detector 5: Any single expense today exceeding ₹10,000."""
    alerts = []
    large = db.query(Expense).filter(
        Expense.expense_date == today,
        Expense.amount > 10000
    ).all()
    for exp in large:
        alerts.append({
            "id": f"large_expense_{exp.id}_{today}",
            "severity": "caution",
            "title": f"Large Expense — {exp.category}",
            "message": f"₹{exp.amount:,.0f} recorded under '{exp.category}': {exp.description or 'No description'}",
            "category": "large_expense",
            "date": str(today),
        })
    return alerts


@router.get("")
def get_alerts(db: Session = Depends(get_db)):
    """Run all 5 detectors and return active alerts."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    check_dates = [today, yesterday]

    all_alerts = []
    all_alerts.extend(_detect_nozzle_mismatch(db, check_dates))
    all_alerts.extend(_detect_meter_mismatch(db, check_dates))
    all_alerts.extend(_detect_missing_shifts(db, check_dates))
    all_alerts.extend(_detect_cash_mismatch(db, today))
    all_alerts.extend(_detect_large_expenses(db, today))
    all_alerts = [alert for alert in all_alerts if alert["id"] not in DISMISSED_ALERT_IDS]

    # Sort: critical first, then warning, then caution
    severity_order = {"critical": 0, "warning": 1, "caution": 2}
    all_alerts.sort(key=lambda a: severity_order.get(a["severity"], 99))

    critical_count = sum(1 for a in all_alerts if a["severity"] == "critical")

    return {
        "alerts": all_alerts,
        "total_count": len(all_alerts),
        "critical_count": critical_count,
    }


@router.post("/clear")
def clear_alerts(db: Session = Depends(get_db)):
    """Dismiss currently active generated alerts for this app session."""
    data = get_alerts(db)
    for alert in data["alerts"]:
        DISMISSED_ALERT_IDS.add(alert["id"])
    return {
        "detail": "Alerts cleared",
        "cleared": len(data["alerts"]),
        "total_count": 0,
        "critical_count": 0,
    }
