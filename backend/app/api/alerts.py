from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.prediction import AlertResponse
from app.services.alert_service import get_alerts, mark_alert_as_read, get_unread_alert_count
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=list[AlertResponse])
def list_alerts(
    patient_id: int | None = None,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List alerts. Doctors see only their assigned patients' alerts."""
    doctor_id = current_user.user_id if current_user.role == "doctor" else None
    return get_alerts(db, patient_id=patient_id, unread_only=unread_only, doctor_id=doctor_id)


@router.get("/unread/count")
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get count of unread alerts."""
    doctor_id = current_user.user_id if current_user.role == "doctor" else None
    count = get_unread_alert_count(db, doctor_id=doctor_id)
    return {"unread_count": count}


@router.patch("/{alert_id}/read")
def mark_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
):
    """Mark an alert as read (doctor only)."""
    alert = mark_alert_as_read(db, alert_id, current_user.user_id)
    return {"message": "Alert marked as read", "alert_id": alert.alert_id}
