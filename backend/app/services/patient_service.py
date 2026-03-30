from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.patient import Patient
from app.models.user import User


def create_patient(db: Session, data: dict, created_by_user_id: int) -> Patient:
    """Create a new patient record."""
    patient = Patient(**data, created_by_user_id=created_by_user_id)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def get_patients_by_status(db: Session, status_filter: str = "active", doctor_id: int | None = None):
    """Get patients filtered by status category."""
    query = db.query(Patient)

    if status_filter == "active":
        query = query.filter(Patient.status == "admitted")
    elif status_filter == "history":
        query = query.filter(Patient.status.in_(["discharged", "transferred"]))

    if doctor_id:
        query = query.filter(Patient.assigned_doctor_id == doctor_id)

    patients = query.order_by(Patient.admission_time.desc()).all()

    # Enrich with doctor names
    result = []
    for p in patients:
        data = {
            "patient_id": p.patient_id,
            "full_name": p.full_name,
            "date_of_birth": p.date_of_birth,
            "age": p.age,
            "gender": p.gender,
            "admission_time": p.admission_time,
            "discharge_time": p.discharge_time,
            "bed_number": p.bed_number,
            "ward_name": p.ward_name,
            "status": p.status,
            "assigned_doctor_id": p.assigned_doctor_id,
            "diagnosis_notes": p.diagnosis_notes,
            "created_by_user_id": p.created_by_user_id,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "doctor_name": None,
        }
        if p.assigned_doctor_id:
            doctor = db.query(User).filter(User.user_id == p.assigned_doctor_id).first()
            if doctor:
                data["doctor_name"] = doctor.full_name
        result.append(data)

    return result


def get_patient_by_id(db: Session, patient_id: int):
    """Get a single patient by ID."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    doctor_name = None
    if patient.assigned_doctor_id:
        doctor = db.query(User).filter(User.user_id == patient.assigned_doctor_id).first()
        if doctor:
            doctor_name = doctor.full_name

    return {
        "patient_id": patient.patient_id,
        "full_name": patient.full_name,
        "date_of_birth": patient.date_of_birth,
        "age": patient.age,
        "gender": patient.gender,
        "admission_time": patient.admission_time,
        "discharge_time": patient.discharge_time,
        "bed_number": patient.bed_number,
        "ward_name": patient.ward_name,
        "status": patient.status,
        "assigned_doctor_id": patient.assigned_doctor_id,
        "diagnosis_notes": patient.diagnosis_notes,
        "created_by_user_id": patient.created_by_user_id,
        "created_at": patient.created_at,
        "updated_at": patient.updated_at,
        "doctor_name": doctor_name,
    }


def update_patient(db: Session, patient_id: int, data: dict) -> Patient:
    """Update patient fields."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    for key, value in data.items():
        if value is not None:
            setattr(patient, key, value)

    db.commit()
    db.refresh(patient)
    return patient
