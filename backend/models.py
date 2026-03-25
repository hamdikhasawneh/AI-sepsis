from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    status = Column(String)
    assigned_doctor_id = Column(Integer, ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=func.now())


class VitalSigns(Base):
    __tablename__ = "vital_signs"

    vital_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"))
    heart_rate = Column(Float)
    respiratory_rate = Column(Float)
    temperature = Column(Float)
    spo2 = Column(Float)
    systolic_bp = Column(Float)
    diastolic_bp = Column(Float)
    mean_bp = Column(Float)
    recorded_at = Column(DateTime, default=func.now())


class LabResult(Base):
    __tablename__ = "lab_results"

    lab_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"))
    lab_name = Column(String)
    lab_value = Column(Float)
    unit = Column(String)
    recorded_at = Column(DateTime, default=func.now())


class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"))
    risk_score = Column(Float)
    risk_level = Column(String)
    model_version = Column(String)
    predicted_at = Column(DateTime, default=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.prediction_id"))
    patient_id = Column(Integer, ForeignKey("patients.patient_id"))
    alert_message = Column(String)
    alert_level = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
