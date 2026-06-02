"""
FastAPI route — Employee Management
CRUD operations for the permanent employee register.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from database.engine import get_db
from database.models import Employee, EmployeeSalary
from api.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeSalaryPaymentCreate
)

router = APIRouter(prefix="/api/employees", tags=["Employees"])


@router.get("", response_model=List[EmployeeResponse])
def get_employees(active_only: bool = True, db: Session = Depends(get_db)):
    """Get all employees (default: active only)."""
    query = db.query(Employee)
    if active_only:
        query = query.filter(Employee.is_active == True)
    employees = query.order_by(Employee.name).all()
    return [
        EmployeeResponse(
            id=e.id, name=e.name, age=e.age, phone=e.phone,
            monthly_salary=e.monthly_salary, is_active=e.is_active,
            created_at=e.created_at,
        ) for e in employees
    ]


@router.post("", response_model=EmployeeResponse)
def create_employee(entry: EmployeeCreate, db: Session = Depends(get_db)):
    """Add a new employee."""
    employee = Employee(
        name=entry.name,
        age=entry.age,
        phone=entry.phone,
        monthly_salary=entry.monthly_salary or 0.0,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return EmployeeResponse(
        id=employee.id, name=employee.name, age=employee.age,
        phone=employee.phone, monthly_salary=employee.monthly_salary,
        is_active=employee.is_active, created_at=employee.created_at,
    )


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(employee_id: int, entry: EmployeeUpdate, db: Session = Depends(get_db)):
    """Update an existing employee."""
    employee = db.query(Employee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if entry.name is not None:
        employee.name = entry.name
    if entry.age is not None:
        employee.age = entry.age
    if entry.phone is not None:
        employee.phone = entry.phone
    if entry.monthly_salary is not None:
        employee.monthly_salary = entry.monthly_salary
    if entry.is_active is not None:
        employee.is_active = entry.is_active

    db.commit()
    db.refresh(employee)
    return EmployeeResponse(
        id=employee.id, name=employee.name, age=employee.age,
        phone=employee.phone, monthly_salary=employee.monthly_salary,
        is_active=employee.is_active, created_at=employee.created_at,
    )


@router.delete("/{employee_id}")
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    """Delete an employee (hard delete)."""
    employee = db.query(Employee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(employee)
    db.commit()
    return {"detail": "Employee deleted", "id": employee_id}


@router.post("/{employee_id}/salary-payments")
def pay_employee_salary(
    employee_id: int,
    entry: EmployeeSalaryPaymentCreate,
    db: Session = Depends(get_db)
):
    """Record an ad-hoc salary payment for an employee."""
    employee = db.query(Employee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if entry.amount <= 0:
        raise HTTPException(status_code=400, detail="Salary amount must be greater than zero")

    paid_date = entry.paid_date or date.today()
    salary = EmployeeSalary(
        employee_name=employee.name,
        designation=f"Age: {employee.age or '-'} | Ph: {employee.phone or '-'}",
        monthly_salary=entry.amount,
        month=paid_date.month,
        year=paid_date.year,
        is_paid=True,
        paid_date=paid_date,
    )
    db.add(salary)
    db.commit()
    db.refresh(salary)

    return {
        "id": salary.id,
        "employee_name": salary.employee_name,
        "amount": salary.monthly_salary,
        "paid_date": salary.paid_date,
    }
