"""
FastAPI route — Nozzle Management
CRUD for nozzles and fuel type assignments.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database.engine import get_db
from database.models import Nozzle, NozzleAssignment, FuelType
from api.schemas.nozzle import (
    NozzleResponse, AssignNozzleRequest, NozzleAssignmentResponse
)

router = APIRouter(prefix="/api/nozzle", tags=["Nozzle Management"])


@router.get("/list", response_model=List[NozzleResponse])
def get_nozzles(db: Session = Depends(get_db)):
    """Get all nozzles with their current fuel type assignment."""
    nozzles = db.query(Nozzle).order_by(Nozzle.nozzle_number).all()
    result = []
    for nozzle in nozzles:
        # Get active assignment
        assignment = db.query(NozzleAssignment).filter_by(
            nozzle_id=nozzle.id, is_active=True
        ).first()

        fuel_name = None
        fuel_type_id = None
        if assignment:
            fuel = db.query(FuelType).filter_by(id=assignment.fuel_type_id).first()
            fuel_name = fuel.name if fuel else None
            fuel_type_id = assignment.fuel_type_id

        result.append(NozzleResponse(
            id=nozzle.id,
            nozzle_number=nozzle.nozzle_number,
            label=nozzle.label,
            is_active=nozzle.is_active,
            assigned_fuel_type=fuel_name,
            assigned_fuel_type_id=fuel_type_id,
        ))
    return result


@router.post("/assign", response_model=NozzleAssignmentResponse)
def assign_nozzle(request: AssignNozzleRequest, db: Session = Depends(get_db)):
    """Assign a fuel type to a nozzle. Deactivates previous assignment."""
    # Validate nozzle exists
    nozzle = db.query(Nozzle).filter_by(id=request.nozzle_id).first()
    if not nozzle:
        raise HTTPException(status_code=404, detail="Nozzle not found")

    # Validate fuel type exists
    fuel = db.query(FuelType).filter_by(id=request.fuel_type_id).first()
    if not fuel:
        raise HTTPException(status_code=404, detail="Fuel type not found")

    # Deactivate existing assignment for this nozzle
    existing = db.query(NozzleAssignment).filter_by(
        nozzle_id=request.nozzle_id, is_active=True
    ).all()
    for a in existing:
        a.is_active = False

    # Create new assignment
    assignment = NozzleAssignment(
        nozzle_id=request.nozzle_id,
        fuel_type_id=request.fuel_type_id,
        is_active=True,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return NozzleAssignmentResponse(
        id=assignment.id,
        nozzle_id=assignment.nozzle_id,
        nozzle_number=nozzle.nozzle_number,
        fuel_type_id=assignment.fuel_type_id,
        fuel_type_name=fuel.name,
        assigned_at=assignment.assigned_at,
        is_active=assignment.is_active,
    )


@router.get("/assignments", response_model=List[NozzleAssignmentResponse])
def get_assignments(db: Session = Depends(get_db)):
    """Get all active nozzle-to-fuel assignments."""
    assignments = db.query(NozzleAssignment).filter_by(is_active=True).all()
    result = []
    for a in assignments:
        nozzle = db.query(Nozzle).filter_by(id=a.nozzle_id).first()
        fuel = db.query(FuelType).filter_by(id=a.fuel_type_id).first()
        result.append(NozzleAssignmentResponse(
            id=a.id,
            nozzle_id=a.nozzle_id,
            nozzle_number=nozzle.nozzle_number if nozzle else 0,
            fuel_type_id=a.fuel_type_id,
            fuel_type_name=fuel.name if fuel else "Unknown",
            assigned_at=a.assigned_at,
            is_active=a.is_active,
        ))
    return result
