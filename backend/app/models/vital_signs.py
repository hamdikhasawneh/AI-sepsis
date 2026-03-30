from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class VitalSign(Base):
    __tablename__ = "vital_signs"

    vital_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    heart_rate = Column(Float, nullable=True)
    respiratory_rate = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    spo2 = Column(Float, nullable=True)
    systolic_bp = Column(Float, nullable=True)
    diastolic_bp = Column(Float, nullable=True)
    mean_bp = Column(Float, nullable=True)
    source = Column(String(20), nullable=False, default="manual")  # manual, monitor
    entered_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="vital_signs")
    entered_by = relationship("User")

    # Indexes for frequent queries
    __table_args__ = (
        Index("ix_vital_signs_patient_recorded", "patient_id", "recorded_at"),
    )

    def __repr__(self):
        return f"<VitalSign patient={self.patient_id} at={self.recorded_at}>"
