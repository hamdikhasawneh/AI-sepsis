"""
Alert Engine Service.

Generates alerts when prediction risk scores exceed the configurable threshold.
Prevents duplicate unread alerts for the same patient.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.prediction import Prediction
from app.models.patient import Patient
from app.models.user import User
from app.services.prediction_service import get_threshold


def check_and_create_alert(db: Session, prediction: Prediction) -> Alert | None:
    """
    Check if a prediction warrants an alert and create one if needed.

    Rules:
    - Only create alert if risk_score >= threshold
    - Prevent duplicate: don't create if unread alert already exists for this patient
    """
    threshold = get_threshold(db)

    if prediction.risk_score < threshold:
        return None

    # Check for existing unread alert for this patient
    existing_unread = (
        db.query(Alert)
        .filter(Alert.patient_id == prediction.patient_id, Alert.is_read == False)
        .first()
    )

    if existing_unread:
        return None  # Don't duplicate

    # Get patient name for alert message
    patient = db.query(Patient).filter(Patient.patient_id == prediction.patient_id).first()
    patient_name = patient.full_name if patient else f"Patient #{prediction.patient_id}"

    # Determine alert level
    alert_level = "critical" if prediction.risk_score >= 0.9 else "high"

    alert = Alert(
        prediction_id=prediction.prediction_id,
        patient_id=prediction.patient_id,
        alert_message=f"⚠️ High sepsis risk detected for {patient_name}. "
                      f"Risk score: {prediction.risk_score:.2%} "
                      f"(threshold: {threshold:.2%})",
        alert_level=alert_level,
        is_read=False,
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def get_alerts(db: Session, patient_id: int | None = None, unread_only: bool = False,
               doctor_id: int | None = None, limit: int = 50):
    """Get alerts with optional filters."""
    query = db.query(Alert)

    if patient_id:
        query = query.filter(Alert.patient_id == patient_id)

    if unread_only:
        query = query.filter(Alert.is_read == False)

    # If doctor, only show alerts for their assigned patients
    if doctor_id:
        assigned_patient_ids = (
            db.query(Patient.patient_id)
            .filter(Patient.assigned_doctor_id == doctor_id)
            .subquery()
        )
        query = query.filter(Alert.patient_id.in_(assigned_patient_ids))

    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()

    # Enrich with patient names
    result = []
    for alert in alerts:
        patient = db.query(Patient).filter(Patient.patient_id == alert.patient_id).first()
        reader = None
        if alert.read_by_user_id:
            reader = db.query(User).filter(User.user_id == alert.read_by_user_id).first()

        result.append({
            "alert_id": alert.alert_id,
            "prediction_id": alert.prediction_id,
            "patient_id": alert.patient_id,
            "patient_name": patient.full_name if patient else "Unknown",
            "alert_message": alert.alert_message,
            "alert_level": alert.alert_level,
            "created_at": alert.created_at,
            "is_read": alert.is_read,
            "read_by_user_id": alert.read_by_user_id,
            "read_by_name": reader.full_name if reader else None,
            "read_at": alert.read_at,
        })

    return result


def mark_alert_as_read(db: Session, alert_id: int, user_id: int) -> Alert:
    """Mark an alert as read (doctor only — enforced at API level)."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.is_read = True
    alert.read_by_user_id = user_id
    alert.read_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(alert)
    return alert


def get_unread_alert_count(db: Session, doctor_id: int | None = None) -> int:
    """Get count of unread alerts, optionally filtered by doctor's assigned patients."""
    query = db.query(Alert).filter(Alert.is_read == False)

    if doctor_id:
        assigned_patient_ids = (
            db.query(Patient.patient_id)
            .filter(Patient.assigned_doctor_id == doctor_id)
            .subquery()
        )
        query = query.filter(Alert.patient_id.in_(assigned_patient_ids))

    return query.count()
