from sqlalchemy import Column, Integer, JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class PatientShapResult(Base):
    """
    Stores live GradientSHAP feature importance values for a specific prediction.
    """
    __tablename__ = "patient_shap_results"

    shap_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    prediction_id = Column(Integer, ForeignKey("predictions.prediction_id"), nullable=False)
    
    # Store top features as a JSON list: [{"feature": "Heart Rate", "shap_value": 0.12, "direction": "Risk +"}, ...]
    shap_values = Column(JSON, nullable=False)
    
    # Optional: model version that generated these values
    model_version = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patient = relationship("Patient", backref="shap_results")
    prediction = relationship("Prediction", backref="shap_result")

    def __repr__(self):
        return f"<PatientShapResult patient={self.patient_id} prediction={self.prediction_id}>"
