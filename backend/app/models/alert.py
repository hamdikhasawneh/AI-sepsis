from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.prediction_id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    alert_message = Column(String(500), nullable=False)
    alert_level = Column(String(20), nullable=False, default="high")  # high, critical
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False, nullable=False)
    read_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    prediction = relationship("Prediction", back_populates="alert")
    patient = relationship("Patient", back_populates="alerts")
    read_by = relationship("User")

    def __repr__(self):
        return f"<Alert patient={self.patient_id} read={self.is_read}>"
