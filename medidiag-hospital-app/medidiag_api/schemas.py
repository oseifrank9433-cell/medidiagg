from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    facility: str
    role: str
    account_type: str = "clinician"  # "clinician" | "admin"
    admin_pin: Optional[str] = None  # required if account_type == "admin"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    account_type: str
    facility: str
    active: bool
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    facility: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None


class UpdateRoleRequest(BaseModel):
    role: str


class SetActiveRequest(BaseModel):
    active: bool


class CreateClinicianRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str


class VitalsIn(BaseModel):
    temperature: Optional[str] = None
    feverDays: Optional[str] = None


class RecordCreate(BaseModel):
    patientName: str
    age: Optional[str] = None
    sex: Optional[str] = None
    vitals: Optional[VitalsIn] = None
    symptoms: List[str]
    # Kept optional for backward compatibility with older frontend builds;
    # the server recomputes the actual result from symptoms and ignores this.
    result: Optional[dict] = None


class RecordOut(BaseModel):
    id: int
    patientName: str
    age: Optional[str] = None
    sex: Optional[str] = None
    vitals: dict
    symptoms: List[str]
    result: dict
    clinicianEmail: str
    clinicianName: str
    createdAt: datetime

    class Config:
        from_attributes = True


class FacilitySettingsOut(BaseModel):
    displayName: str
    address: str = ""
    contact: str = ""
    confidenceThreshold: float


class FacilitySettingsIn(BaseModel):
    displayName: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    confidenceThreshold: float
