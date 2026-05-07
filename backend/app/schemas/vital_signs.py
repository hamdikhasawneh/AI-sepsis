from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime


class VitalCreate(BaseModel):
    patient_id: int
    heart_rate: float | None = None
    respiratory_rate: float | None = None
    temperature: float | None = None
    spo2: float | None = None
    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    mean_bp: float | None = None
    source: str = "manual"  # manual or monitor


class VitalResponse(BaseModel):
    vital_id: int
    patient_id: int
    recorded_at: datetime | None = None
    heart_rate: float | None = None
    respiratory_rate: float | None = None
    temperature: float | None = None
    spo2: float | None = None
    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    mean_bp: float | None = None
    source: str
    entered_by_user_id: int | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
