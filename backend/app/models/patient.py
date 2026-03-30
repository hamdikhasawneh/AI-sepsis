from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(10), nullable=True)  # male, female, other
    admission_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    discharge_time = Column(DateTime(timezone=True), nullable=True)
    bed_number = Column(String(20), nullable=True)
    ward_name = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="admitted")  # admitted, discharged, transferred
    assigned_doctor_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    diagnosis_notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    assigned_doctor = relationship(
        "User", back_populates="assigned_patients", foreign_keys=[assigned_doctor_id]
    )
    created_by_user = relationship(
        "User", back_populates="created_patients", foreign_keys=[created_by_user_id]
    )
    vital_signs = relationship("VitalSign", back_populates="patient", order_by="VitalSign.recorded_at.desc()")
    predictions = relationship("Prediction", back_populates="patient", order_by="Prediction.predicted_at.desc()")
    alerts = relationship("Alert", back_populates="patient", order_by="Alert.created_at.desc()")

    def __repr__(self):
        return f"<Patient {self.full_name} ({self.status})>"
