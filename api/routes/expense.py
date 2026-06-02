"""
FastAPI route — Expense Management
Handles daily expenses, listings, and category breakdowns.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import date

from database.engine import get_db
from database.models import Expense
from api.schemas.expense import ExpenseCreateRequest, ExpenseResponse, ExpenseSummary
from config import EXPENSE_CATEGORIES

router = APIRouter(prefix="/api/expense", tags=["Expense Management"])


@router.post("/entry", response_model=ExpenseResponse)
def create_expense(request: ExpenseCreateRequest, db: Session = Depends(get_db)):
    """Record a new daily expense."""
    if request.category not in EXPENSE_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid expense category. Must be one of {EXPENSE_CATEGORIES}"
        )

    expense = Expense(
        expense_date=request.expense_date,
        category=request.category,
        amount=request.amount,
        description=request.description
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    return ExpenseResponse(
        id=expense.id,
        expense_date=expense.expense_date,
        category=expense.category,
        amount=expense.amount,
        description=expense.description,
        created_at=expense.created_at
    )


@router.get("/list", response_model=List[ExpenseResponse])
def get_expenses(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List operational expenses with optional filters."""
    query = db.query(Expense)
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    if category:
        query = query.filter(Expense.category == category)

    expenses = query.order_by(desc(Expense.expense_date)).all()
    return [
        ExpenseResponse(
            id=e.id,
            expense_date=e.expense_date,
            category=e.category,
            amount=e.amount,
            description=e.description,
            created_at=e.created_at
        ) for e in expenses
    ]


@router.get("/summary", response_model=ExpenseSummary)
def get_expense_summary(
    expense_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get operational expense summary grouped by category for a specific date."""
    if expense_date is None:
        expense_date = date.today()

    expenses = db.query(Expense).filter(Expense.expense_date == expense_date).all()
    total_amount = sum(e.amount for e in expenses)

    # Group by category
    cats = {}
    for e in expenses:
        if e.category not in cats:
            cats[e.category] = 0.0
        cats[e.category] += e.amount

    breakdown = [{"category": k, "amount": v} for k, v in cats.items()]

    return ExpenseSummary(
        date=expense_date,
        total_amount=total_amount,
        category_breakdown=breakdown
    )


@router.delete("/entry/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    """Delete an expense entry."""
    expense = db.query(Expense).filter_by(id=expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense entry not found")

    db.delete(expense)
    db.commit()

    return {"detail": "Expense deleted", "id": expense_id}

