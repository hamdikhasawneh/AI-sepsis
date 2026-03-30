import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.vital_signs import VitalSign
from app.models.patient import Patient


def create_vital(db: Session, data: dict, entered_by_user_id: int | None = None) -> VitalSign:
    """Create a new vital sign record."""
    vital = VitalSign(
        **data,
        entered_by_user_id=entered_by_user_id,
    )
    db.add(vital)
    db.commit()
    db.refresh(vital)
    return vital


def get_patient_vitals(db: Session, patient_id: int, hours: int | None = None):
    """Get vital signs for a patient, optionally limited to the last N hours."""
    query = db.query(VitalSign).filter(VitalSign.patient_id == patient_id)

    if hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = query.filter(VitalSign.recorded_at >= cutoff)

    return query.order_by(VitalSign.recorded_at.desc()).all()


def generate_simulated_vitals(db: Session):
    """Generate simulated monitor vitals for all admitted patients."""
    admitted_patients = db.query(Patient).filter(Patient.status == "admitted").all()

    for patient in admitted_patients:
        vital = VitalSign(
            patient_id=patient.patient_id,
            recorded_at=datetime.now(timezone.utc),
            heart_rate=round(random.uniform(60, 120), 1),
            respiratory_rate=round(random.uniform(12, 30), 1),
            temperature=round(random.uniform(36.0, 39.5), 1),
            spo2=round(random.uniform(88, 100), 1),
            systolic_bp=round(random.uniform(90, 160), 1),
            diastolic_bp=round(random.uniform(50, 100), 1),
            mean_bp=round(random.uniform(65, 120), 1),
            source="monitor",
        )
        db.add(vital)

    db.commit()
    return len(admitted_patients)
