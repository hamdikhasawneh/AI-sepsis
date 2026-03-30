from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    predicted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)  # low, medium, high, critical
    threshold_used = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True, default="mock-v1")
    input_window_hours = Column(Integer, nullable=True, default=6)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="predictions")
    alert = relationship("Alert", back_populates="prediction", uselist=False)

    def __repr__(self):
        return f"<Prediction patient={self.patient_id} score={self.risk_score}>"
