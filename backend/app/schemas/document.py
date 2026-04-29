from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentResponse(BaseModel):
    id: int
    patient_id: str
    file_name: str
    file_path: str
    uploaded_at: datetime

    class Config:
        from_attributes = True
