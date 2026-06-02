"""Pydantic schemas for authentication."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str


class AdminUserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    is_active: bool
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True
