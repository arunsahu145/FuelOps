"""Pydantic schemas for nozzle management."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NozzleResponse(BaseModel):
    id: int
    nozzle_number: int
    label: Optional[str] = None
    is_active: bool
    assigned_fuel_type: Optional[str] = None
    assigned_fuel_type_id: Optional[int] = None

    class Config:
        from_attributes = True


class AssignNozzleRequest(BaseModel):
    nozzle_id: int
    fuel_type_id: int


class NozzleAssignmentResponse(BaseModel):
    id: int
    nozzle_id: int
    nozzle_number: int
    fuel_type_id: int
    fuel_type_name: str
    assigned_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
