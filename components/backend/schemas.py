from pydantic import BaseModel, EmailStr
from typing import Optional

class RegisterIn(BaseModel):
    type: str  # "admin" or "staff"
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = None
    department: Optional[str] = None

class LoginIn(BaseModel):
    type: str
    email: EmailStr
    password: str

class RoleIn(BaseModel):
    name: str

class DeptIn(BaseModel):
    name: str

class ItemIn(BaseModel):
    department: str
    type: str
    name: str
    amount_needed: int

class ItemUpdate(BaseModel):
    department: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    amount_needed: Optional[int] = None