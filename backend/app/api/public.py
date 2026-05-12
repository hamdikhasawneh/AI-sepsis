from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.patient import Patient
from app.models.prediction import Prediction
from app.models.vital_signs import VitalSign

router = APIRouter()

@router.get("/stats")
def get_public_stats(db: Session = Depends(get_db)):
    """Get high-level stats for the landing page without auth."""
    total_patients = db.query(Patient).filter(Patient.status == "admitted").count()
    high_risk = db.query(Patient).join(Prediction).filter(
        Patient.status == "admitted",
        Prediction.risk_level.in_(["high", "critical"])
    ).distinct().count()
    
    return {
        "admitted_patients": total_patients,
        "high_risk_patients": high_risk,
        "active_monitors": total_patients, # Assuming all admitted are monitored
        "avg_lead_time": "28.2 Hours" # Hardcoded based on model performance
    }
