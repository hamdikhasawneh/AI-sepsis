from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate, PatientNotesUpdate
from app.services.patient_service import (
    create_patient,
    get_patients_by_status,
    get_patient_by_id,
    update_patient,
)
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=PatientResponse)
def create_new_patient(
    request: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "nurse")),
):
    """Create a new patient (admin or nurse only)."""
    return create_patient(db, request.model_dump(), current_user.user_id)


@router.get("/", response_model=list[PatientResponse])
def list_patients(
    status_filter: str = "active",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List patients. Doctors see only their assigned patients."""
    doctor_id = None
    if current_user.role == "doctor":
        doctor_id = current_user.user_id

    return get_patients_by_status(db, status_filter, doctor_id)


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get patient details."""
    patient = get_patient_by_id(db, patient_id)

    # Doctors can only view their assigned patients
    if current_user.role == "doctor" and patient["assigned_doctor_id"] != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your assigned patients",
        )

    return patient


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient_info(
    patient_id: int,
    request: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update patient info. Admin: full edit. Nurse: limited edit. Doctor: no edit via this endpoint."""
    if current_user.role == "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctors cannot edit patient info. Use the notes endpoint.",
        )

    update_data = request.model_dump(exclude_unset=True)

    # Nurses cannot change assigned_doctor_id or status
    if current_user.role == "nurse":
        restricted_fields = {"assigned_doctor_id", "status", "discharge_time"}
        for field in restricted_fields:
            update_data.pop(field, None)

    patient = update_patient(db, patient_id, update_data)
    return get_patient_by_id(db, patient_id)


@router.patch("/{patient_id}/notes")
def update_patient_notes(
    patient_id: int,
    request: PatientNotesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor", "admin")),
):
    """Update patient diagnosis notes (doctor or admin)."""
    patient = update_patient(db, patient_id, {"diagnosis_notes": request.diagnosis_notes})
    return {"message": "Notes updated", "patient_id": patient_id}
