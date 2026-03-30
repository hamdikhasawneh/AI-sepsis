from pydantic import BaseModel
from datetime import datetime


class PredictionResponse(BaseModel):
    prediction_id: int
    patient_id: int
    predicted_at: datetime | None = None
    risk_score: float
    risk_level: str
    threshold_used: float | None = None
    model_version: str | None = None
    input_window_hours: int | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    alert_id: int
    prediction_id: int | None = None
    patient_id: int
    patient_name: str | None = None
    alert_message: str
    alert_level: str
    created_at: datetime | None = None
    is_read: bool
    read_by_user_id: int | None = None
    read_by_name: str | None = None
    read_at: datetime | None = None

    class Config:
        from_attributes = True


class SettingResponse(BaseModel):
    setting_id: int | None = None
    key: str
    value: str
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    value: str
