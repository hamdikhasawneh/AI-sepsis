from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.prediction import PredictionResponse
from app.services.prediction_service import get_patient_predictions, get_latest_prediction, get_shap_for_patient
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/{patient_id}", response_model=list[PredictionResponse])
def list_patient_predictions(
    patient_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get prediction history for a patient."""
    return get_patient_predictions(db, patient_id, limit)


@router.get("/{patient_id}/latest", response_model=Optional[PredictionResponse])
def get_patient_latest_prediction(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the latest prediction for a patient."""
    return get_latest_prediction(db, patient_id)


@router.get("/{patient_id}/shap")
def get_patient_shap(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get GradientSHAP feature importance for a patient.
    Returns top 8 features with SHAP values for the AI Reasoning tab in the UI.
    """
    result = get_shap_for_patient(patient_id)
    if result is None:
        return {
            "patient_id": patient_id,
            "features": [],
            "message": "SHAP values not available for this patient"
        }
    return result
