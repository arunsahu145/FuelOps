"""FastAPI route - Customer credit, repayment, ledger, and aging."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from database.engine import get_db
from database.models import Customer, CustomerCredit, CustomerRepayment
from api.schemas.credit import (
    AgingBucket, AgingReport, CreditCreate, CreditResponse, CreditSummary,
    CustomerCreate, CustomerResponse, LedgerEntry, OutstandingCustomer,
    RepaymentCreate, RepaymentResponse,
)
from utils.helpers import get_month_range

router = APIRouter(prefix="/api/credit", tags=["Customer Credit"])

PAYMENT_MODES = ["Cash", "Paytm", "PhonePe", "UPI", "Bank Transfer", "Cheque", "Other"]
OVERDUE_AFTER_DAYS = 30


def _clean_phone(phone: str) -> str:
    return "".join(ch for ch in (phone or "") if ch.isdigit())


def _next_customer_code(db: Session) -> str:
    latest_id = db.query(func.max(Customer.id)).scalar() or 0
    return f"CUST-{latest_id + 1:05d}"


def _totals(db: Session, customer_id: int) -> tuple[float, float, float]:
    total_credit = db.query(func.coalesce(func.sum(CustomerCredit.amount), 0.0)).filter(
        CustomerCredit.customer_id == customer_id
    ).scalar() or 0.0
    total_repaid = db.query(func.coalesce(func.sum(CustomerRepayment.amount), 0.0)).filter(
        CustomerRepayment.customer_id == customer_id
    ).scalar() or 0.0
    outstanding = max(float(total_credit) - float(total_repaid), 0.0)
    return float(total_credit), float(total_repaid), outstanding


def _oldest_unpaid_date(db: Session, customer_id: int) -> Optional[date]:
    total_repaid = db.query(func.coalesce(func.sum(CustomerRepayment.amount), 0.0)).filter(
        CustomerRepayment.customer_id == customer_id
    ).scalar() or 0.0
    remaining_repaid = float(total_repaid)
    credits = db.query(CustomerCredit).filter_by(customer_id=customer_id).order_by(
        CustomerCredit.credit_date, CustomerCredit.id
    ).all()
    for credit in credits:
        if remaining_repaid >= credit.amount:
            remaining_repaid -= credit.amount
            continue
        return credit.due_date or credit.credit_date
    return None


def _outstanding_row(db: Session, customer: Customer, as_of: Optional[date] = None) -> Optional[OutstandingCustomer]:
    total_credit, total_repaid, outstanding = _totals(db, customer.id)
    if outstanding <= 0:
        return None

    last_credit = db.query(CustomerCredit).filter_by(customer_id=customer.id).order_by(
        desc(CustomerCredit.credit_date), desc(CustomerCredit.id)
    ).first()
    last_repay = db.query(CustomerRepayment).filter_by(customer_id=customer.id).order_by(
        desc(CustomerRepayment.repayment_date), desc(CustomerRepayment.id)
    ).first()
    unpaid_date = _oldest_unpaid_date(db, customer.id)
    today = as_of or date.today()
    overdue_days = max((today - unpaid_date).days - OVERDUE_AFTER_DAYS, 0) if unpaid_date else 0

    return OutstandingCustomer(
        customer_id=customer.id,
        customer_code=customer.customer_code,
        customer_name=customer.name,
        phone=customer.phone,
        total_credit=total_credit,
        total_repaid=total_repaid,
        outstanding=outstanding,
        last_credit_date=last_credit.credit_date if last_credit else None,
        last_repayment_date=last_repay.repayment_date if last_repay else None,
        oldest_unpaid_date=unpaid_date,
        overdue_days=overdue_days,
        status="Overdue" if overdue_days > 0 else "Open",
    )


def _customer_response(db: Session, customer: Customer) -> CustomerResponse:
    total_credit, total_repaid, outstanding = _totals(db, customer.id)
    return CustomerResponse(
        id=customer.id,
        customer_code=customer.customer_code,
        name=customer.name,
        phone=customer.phone,
        address=customer.address,
        is_active=customer.is_active,
        created_at=customer.created_at,
        total_credit=total_credit,
        total_repaid=total_repaid,
        outstanding=outstanding,
    )


@router.post("/customers", response_model=CustomerResponse)
def create_customer(request: CustomerCreate, db: Session = Depends(get_db)):
    phone = _clean_phone(request.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    if db.query(Customer).filter(Customer.phone == phone).first():
        raise HTTPException(status_code=400, detail="Customer with this phone already exists")

    customer = Customer(
        customer_code=_next_customer_code(db),
        name=request.name.strip(),
        phone=phone,
        address=(request.address or "").strip() or None,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return _customer_response(db, customer)


@router.get("/customers", response_model=List[CustomerResponse])
def list_customers(search: Optional[str] = None, phone: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Customer).filter(Customer.is_active == True)
    if phone:
        query = query.filter(Customer.phone.like(f"{_clean_phone(phone)}%"))
    if search:
        term = f"%{search.strip()}%"
        filters = [
            Customer.name.ilike(term),
            Customer.customer_code.ilike(term),
        ]
        phone_digits = _clean_phone(search)
        if phone_digits:
            filters.append(Customer.phone.like(f"%{phone_digits}%"))
        query = query.filter(or_(*filters))
    return [_customer_response(db, customer) for customer in query.order_by(Customer.name).all()]


@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter_by(id=customer_id, is_active=True).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    _, _, outstanding = _totals(db, customer.id)
    if outstanding > 0:
        raise HTTPException(
            status_code=400,
            detail="Customer has outstanding credit. Clear repayment before deleting.",
        )
    customer.is_active = False
    db.commit()
    return {"detail": "Customer deleted", "id": customer_id}


@router.post("/credits", response_model=CreditResponse)
def create_credit(request: CreditCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter_by(id=request.customer_id, is_active=True).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if request.due_date and request.due_date < request.credit_date:
        raise HTTPException(status_code=400, detail="Due date cannot be before credit date")

    credit = CustomerCredit(
        customer_id=customer.id,
        credit_date=request.credit_date,
        amount=request.amount,
        due_date=request.due_date,
        remarks=request.remarks,
    )
    db.add(credit)
    db.commit()
    db.refresh(credit)
    return CreditResponse(
        id=credit.id, customer_id=customer.id, customer_code=customer.customer_code,
        customer_name=customer.name, phone=customer.phone, credit_date=credit.credit_date,
        amount=credit.amount, due_date=credit.due_date, remarks=credit.remarks,
        created_at=credit.created_at,
    )


@router.get("/credits", response_model=List[CreditResponse])
def list_credits(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(CustomerCredit).join(Customer)
    if start_date:
        query = query.filter(CustomerCredit.credit_date >= start_date)
    if end_date:
        query = query.filter(CustomerCredit.credit_date <= end_date)
    if customer_id:
        query = query.filter(CustomerCredit.customer_id == customer_id)
    credits = query.order_by(desc(CustomerCredit.credit_date), desc(CustomerCredit.id)).all()
    return [
        CreditResponse(
            id=c.id, customer_id=c.customer_id, customer_code=c.customer.customer_code,
            customer_name=c.customer.name, phone=c.customer.phone, credit_date=c.credit_date,
            amount=c.amount, due_date=c.due_date, remarks=c.remarks, created_at=c.created_at,
        )
        for c in credits
    ]


@router.get("/outstanding", response_model=List[OutstandingCustomer])
def list_outstanding(phone: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Customer).filter(Customer.is_active == True)
    if phone:
        query = query.filter(Customer.phone.like(f"{_clean_phone(phone)}%"))
    rows = []
    for customer in query.order_by(Customer.name).all():
        row = _outstanding_row(db, customer)
        if row:
            rows.append(row)
    return rows


@router.post("/repayments", response_model=RepaymentResponse)
def create_repayment(request: RepaymentCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter_by(id=request.customer_id, is_active=True).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if request.mode not in PAYMENT_MODES:
        raise HTTPException(status_code=400, detail=f"Payment mode must be one of {PAYMENT_MODES}")
    _, _, outstanding = _totals(db, customer.id)
    if outstanding <= 0:
        raise HTTPException(status_code=400, detail="Customer has no outstanding credit")
    if request.amount > outstanding:
        raise HTTPException(status_code=400, detail="Repayment cannot exceed outstanding amount")

    repayment = CustomerRepayment(
        customer_id=customer.id,
        repayment_date=request.repayment_date,
        amount=request.amount,
        mode=request.mode,
        reference_number=request.reference_number,
        remarks=request.remarks,
    )
    db.add(repayment)
    db.commit()
    db.refresh(repayment)
    _, _, outstanding_after = _totals(db, customer.id)
    return RepaymentResponse(
        id=repayment.id, customer_id=customer.id, customer_code=customer.customer_code,
        customer_name=customer.name, phone=customer.phone, repayment_date=repayment.repayment_date,
        amount=repayment.amount, mode=repayment.mode,
        reference_number=repayment.reference_number, remarks=repayment.remarks,
        outstanding_after=outstanding_after, created_at=repayment.created_at,
    )


@router.get("/repayments", response_model=List[RepaymentResponse])
def list_repayments(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(CustomerRepayment).join(Customer)
    if start_date:
        query = query.filter(CustomerRepayment.repayment_date >= start_date)
    if end_date:
        query = query.filter(CustomerRepayment.repayment_date <= end_date)
    if customer_id:
        query = query.filter(CustomerRepayment.customer_id == customer_id)
    repayments = query.order_by(desc(CustomerRepayment.repayment_date), desc(CustomerRepayment.id)).all()
    return [
        RepaymentResponse(
            id=r.id, customer_id=r.customer_id, customer_code=r.customer.customer_code,
            customer_name=r.customer.name, phone=r.customer.phone,
            repayment_date=r.repayment_date, amount=r.amount, mode=r.mode,
            reference_number=r.reference_number, remarks=r.remarks,
            outstanding_after=_totals(db, r.customer_id)[2], created_at=r.created_at,
        )
        for r in repayments
    ]


@router.get("/ledger/{customer_id}", response_model=List[LedgerEntry])
def customer_ledger(customer_id: int, db: Session = Depends(get_db)):
    if not db.query(Customer).filter_by(id=customer_id).first():
        raise HTTPException(status_code=404, detail="Customer not found")

    entries = []
    for c in db.query(CustomerCredit).filter_by(customer_id=customer_id).all():
        entries.append((c.credit_date, c.created_at, LedgerEntry(
            entry_date=c.credit_date, entry_type="Credit", debit=c.amount,
            credit=0.0, balance=0.0, remarks=c.remarks,
        )))
    for r in db.query(CustomerRepayment).filter_by(customer_id=customer_id).all():
        entries.append((r.repayment_date, r.created_at, LedgerEntry(
            entry_date=r.repayment_date, entry_type="Repayment", debit=0.0,
            credit=r.amount, balance=0.0, mode=r.mode,
            reference_number=r.reference_number, remarks=r.remarks,
        )))

    balance = 0.0
    ledger = []
    for _, _, entry in sorted(entries, key=lambda item: (item[0], item[1])):
        balance += entry.debit - entry.credit
        entry.balance = max(balance, 0.0)
        ledger.append(entry)
    return ledger


@router.get("/summary", response_model=CreditSummary)
def credit_summary(
    summary_date: Optional[date] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
):
    today = summary_date or date.today()
    today_credits = db.query(func.coalesce(func.sum(CustomerCredit.amount), 0.0)).filter(
        CustomerCredit.credit_date == today
    ).scalar() or 0.0
    today_repayments = db.query(func.coalesce(func.sum(CustomerRepayment.amount), 0.0)).filter(
        CustomerRepayment.repayment_date == today
    ).scalar() or 0.0
    total_credit = db.query(func.coalesce(func.sum(CustomerCredit.amount), 0.0)).scalar() or 0.0
    total_repaid = db.query(func.coalesce(func.sum(CustomerRepayment.amount), 0.0)).scalar() or 0.0
    outstanding = max(float(total_credit) - float(total_repaid), 0.0)

    overdue = 0
    for customer in db.query(Customer).filter(Customer.is_active == True).all():
        row = _outstanding_row(db, customer)
        if row and row.status == "Overdue":
            overdue += 1

    period_credits = today_credits
    period_repayments = today_repayments
    if year and month:
        first_day, last_day = get_month_range(year, month)
        period_credits = db.query(func.coalesce(func.sum(CustomerCredit.amount), 0.0)).filter(
            CustomerCredit.credit_date >= first_day,
            CustomerCredit.credit_date <= last_day,
        ).scalar() or 0.0
        period_repayments = db.query(func.coalesce(func.sum(CustomerRepayment.amount), 0.0)).filter(
            CustomerRepayment.repayment_date >= first_day,
            CustomerRepayment.repayment_date <= last_day,
        ).scalar() or 0.0

    return CreditSummary(
        total_credits_given_today=float(today_credits),
        total_credits_outstanding=outstanding,
        total_repayment_amount_done=float(today_repayments),
        overdue_customers=overdue,
        total_credits_in_period=float(period_credits),
        total_repayments_in_period=float(period_repayments),
    )


@router.get("/aging", response_model=AgingReport)
def aging_report(as_of: Optional[date] = None, db: Session = Depends(get_db)):
    as_of = as_of or date.today()
    buckets = {
        "0-30 days": {"count": 0, "amount": 0.0},
        "31-60 days": {"count": 0, "amount": 0.0},
        "61-90 days": {"count": 0, "amount": 0.0},
        "90+ days": {"count": 0, "amount": 0.0},
    }
    customers = []
    for customer in db.query(Customer).filter(Customer.is_active == True).all():
        row = _outstanding_row(db, customer, as_of=as_of)
        if not row:
            continue
        customers.append(row)
        age = (as_of - row.oldest_unpaid_date).days if row.oldest_unpaid_date else 0
        if age <= 30:
            bucket = "0-30 days"
        elif age <= 60:
            bucket = "31-60 days"
        elif age <= 90:
            bucket = "61-90 days"
        else:
            bucket = "90+ days"
        buckets[bucket]["count"] += 1
        buckets[bucket]["amount"] += row.outstanding

    return AgingReport(
        as_of=as_of,
        buckets=[
            AgingBucket(bucket=name, customer_count=data["count"], outstanding=data["amount"])
            for name, data in buckets.items()
        ],
        customers=sorted(customers, key=lambda c: c.overdue_days, reverse=True),
    )
