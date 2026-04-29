from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LabResultCreate(BaseModel):
    patient_id: str
    test_name: str
    value: float
    unit: str
    reference_range: str
    status: str

class LabResultResponse(LabResultCreate):
    id: int
    recorded_at: datetime

    class Config:
        from_attributes = True
