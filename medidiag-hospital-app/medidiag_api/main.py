import os
from datetime import datetime, timezone
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import Base, engine, get_db
from engine import SYMPTOMS, run_diagnosis

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MediDiag API")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.up\.railway\.app|http://localhost:5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health / diagnosis endpoints (unchanged from the earlier pure-inference API)
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "MediDiag API is running"}


@app.get("/symptoms")
def get_symptoms():
    return {"symptoms": SYMPTOMS}


class DiagnosisRequest(schemas.BaseModel):
    symptoms: List[str]


class DiagnosisResponse(schemas.BaseModel):
    diagnosis: str
    drug: str
    malaria_pct: float
    typhoid_pct: float


@app.post("/predict", response_model=DiagnosisResponse)
def predict(request: DiagnosisRequest):
    invalid = [s for s in request.symptoms if s not in SYMPTOMS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown symptoms: {invalid}")
    if len(request.symptoms) == 0:
        raise HTTPException(status_code=400, detail="At least one symptom is required.")

    prediction, drug, malaria_pct, typhoid_pct = run_diagnosis(request.symptoms)
    return DiagnosisResponse(diagnosis=prediction, drug=drug, malaria_pct=malaria_pct, typhoid_pct=typhoid_pct)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/auth/signup", response_model=schemas.TokenResponse)
def signup(payload: schemas.SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    if payload.account_type == "admin":
        if payload.admin_pin != auth.ADMIN_SIGNUP_PIN:
            raise HTTPException(status_code=403, detail="Incorrect admin PIN.")

    user = models.User(
        name=payload.name,
        email=payload.email,
        password_hash=auth.hash_password(payload.password),
        role="Administrator" if payload.account_type == "admin" else payload.role,
        account_type=payload.account_type,
        facility=payload.facility,
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = auth.create_access_token({"sub": user.email})
    return schemas.TokenResponse(access_token=token, user=user)


@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    if not user.active:
        raise HTTPException(status_code=403, detail="This account has been deactivated. Contact your facility admin.")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    token = auth.create_access_token({"sub": user.email})
    return schemas.TokenResponse(access_token=token, user=user)


@app.get("/auth/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@app.put("/auth/me", response_model=schemas.UserOut)
def update_me(
    payload: schemas.UpdateProfileRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if payload.name is not None:
        current_user.name = payload.name
    if payload.email is not None and payload.email != current_user.email:
        clash = db.query(models.User).filter(models.User.email == payload.email).first()
        if clash:
            raise HTTPException(status_code=400, detail="An account with this email already exists.")
        current_user.email = payload.email
    if payload.facility is not None:
        current_user.facility = payload.facility
    if payload.role is not None:
        current_user.role = payload.role
    if payload.password:
        if len(payload.password) < 6:
            raise HTTPException(status_code=400, detail="New password should be at least 6 characters.")
        current_user.password_hash = auth.hash_password(payload.password)

    db.commit()
    db.refresh(current_user)
    return current_user


# ---------------------------------------------------------------------------
# Patient records (clinician-scoped)
# ---------------------------------------------------------------------------

def _record_to_out(r: models.Record) -> dict:
    return {
        "id": r.id,
        "patientName": r.patient_name,
        "age": r.age,
        "sex": r.sex,
        "vitals": {"temperature": r.vitals_temperature, "feverDays": r.vitals_fever_days},
        "symptoms": r.symptoms,
        "result": {
            "diagnosis": r.diagnosis,
            "drug": r.drug,
            "malariaPct": r.malaria_pct,
            "typhoidPct": r.typhoid_pct,
        },
        "clinicianEmail": r.clinician.email,
        "clinicianName": r.clinician.name,
        "createdAt": r.created_at,
    }


@app.post("/records", response_model=schemas.RecordOut)
def create_record(
    payload: schemas.RecordCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    # The diagnosis is recomputed here from the symptoms rather than trusted
    # from payload.result, so a record's stored result always matches what
    # the model actually produces for those symptoms (payload.result is kept
    # only for backward compatibility with older frontend builds and is
    # otherwise ignored).
    invalid = [s for s in payload.symptoms if s not in SYMPTOMS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown symptoms: {invalid}")
    if len(payload.symptoms) == 0:
        raise HTTPException(status_code=400, detail="At least one symptom is required.")

    prediction, drug, malaria_pct, typhoid_pct = run_diagnosis(payload.symptoms)

    settings = (
        db.query(models.FacilitySettings)
        .filter(models.FacilitySettings.facility == current_user.facility)
        .first()
    )
    threshold = settings.confidence_threshold if settings else 60.0
    if max(malaria_pct, typhoid_pct) < threshold:
        diagnosis, drug = "Unknown / Refer to Clinician", "No automatic prescription. Recommend laboratory testing."
    else:
        diagnosis = prediction

    vitals = payload.vitals or schemas.VitalsIn()
    record = models.Record(
        clinician_id=current_user.id,
        patient_name=payload.patientName,
        age=payload.age,
        sex=payload.sex,
        vitals_temperature=vitals.temperature,
        vitals_fever_days=vitals.feverDays,
        symptoms=payload.symptoms,
        diagnosis=diagnosis,
        drug=drug,
        malaria_pct=malaria_pct,
        typhoid_pct=typhoid_pct,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _record_to_out(record)


@app.get("/records", response_model=List[schemas.RecordOut])
def list_my_records(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    records = (
        db.query(models.Record)
        .filter(models.Record.clinician_id == current_user.id)
        .order_by(models.Record.created_at.desc())
        .all()
    )
    return [_record_to_out(r) for r in records]


@app.get("/records/{record_id}", response_model=schemas.RecordOut)
def get_record(
    record_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(models.Record).filter(models.Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")
    # A clinician can view their own records; an admin can view any record at their facility.
    if record.clinician_id != current_user.id and not (
        current_user.account_type == "admin" and record.clinician.facility == current_user.facility
    ):
        raise HTTPException(status_code=403, detail="Not authorized to view this record.")
    return _record_to_out(record)


@app.delete("/records/{record_id}")
def delete_record(
    record_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(models.Record).filter(models.Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")
    if record.clinician_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this record.")
    db.delete(record)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Admin: facility-wide records and clinician management
# ---------------------------------------------------------------------------

@app.get("/admin/records", response_model=List[schemas.RecordOut])
def list_facility_records(
    current_user: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    records = (
        db.query(models.Record)
        .join(models.User)
        .filter(models.User.facility == current_user.facility)
        .order_by(models.Record.created_at.desc())
        .all()
    )
    return [_record_to_out(r) for r in records]


@app.delete("/admin/records")
def clear_facility_records(
    current_user: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    (
        db.query(models.Record)
        .filter(models.Record.clinician_id.in_(
            db.query(models.User.id).filter(models.User.facility == current_user.facility)
        ))
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"cleared": True}


@app.get("/admin/users", response_model=List[schemas.UserOut])
def list_facility_users(
    current_user: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.User)
        .filter(models.User.facility == current_user.facility, models.User.account_type != "admin")
        .all()
    )


@app.post("/admin/users", response_model=schemas.UserOut)
def create_clinician(
    payload: schemas.CreateClinicianRequest,
    current_user: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = models.User(
        name=payload.name,
        email=payload.email,
        password_hash=auth.hash_password(payload.password),
        role=payload.role,
        account_type="clinician",
        facility=current_user.facility,
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.patch("/admin/users/{user_id}/role", response_model=schemas.UserOut)
def update_user_role(
    user_id: int,
    payload: schemas.UpdateRoleRequest,
    current_user: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.facility == current_user.facility).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@app.patch("/admin/users/{user_id}/active", response_model=schemas.UserOut)
def set_user_active(
    user_id: int,
    payload: schemas.SetActiveRequest,
    current_user: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.facility == current_user.facility).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.active = payload.active
    db.commit()
    db.refresh(user)
    return user


@app.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account while logged in.")
    user = db.query(models.User).filter(models.User.id == user_id, models.User.facility == current_user.facility).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    db.delete(user)  # cascades to their records, via the relationship in models.py
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Facility settings
# ---------------------------------------------------------------------------

@app.get("/facility-settings", response_model=schemas.FacilitySettingsOut)
def get_facility_settings(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    settings = db.query(models.FacilitySettings).filter(models.FacilitySettings.facility == current_user.facility).first()
    if not settings:
        return schemas.FacilitySettingsOut(displayName=current_user.facility, address="", contact="", confidenceThreshold=60.0)
    return schemas.FacilitySettingsOut(
        displayName=settings.display_name or current_user.facility,
        address=settings.address or "",
        contact=settings.contact or "",
        confidenceThreshold=settings.confidence_threshold,
    )


@app.put("/facility-settings", response_model=schemas.FacilitySettingsOut)
def update_facility_settings(
    payload: schemas.FacilitySettingsIn,
    current_user: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    settings = db.query(models.FacilitySettings).filter(models.FacilitySettings.facility == current_user.facility).first()
    if not settings:
        settings = models.FacilitySettings(facility=current_user.facility)
        db.add(settings)

    settings.display_name = payload.displayName
    settings.address = payload.address
    settings.contact = payload.contact
    settings.confidence_threshold = payload.confidenceThreshold

    db.commit()
    db.refresh(settings)
    return schemas.FacilitySettingsOut(
        displayName=settings.display_name or current_user.facility,
        address=settings.address or "",
        contact=settings.contact or "",
        confidenceThreshold=settings.confidence_threshold,
    )
