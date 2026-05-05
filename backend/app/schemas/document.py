from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ExtractedLab(BaseModel):
    """A single lab result extracted from a PDF via OCR."""
    test_name: str
    value: float
    unit: str
    reference_range: str
    status: str


class DocumentResponse(BaseModel):
    id: int
    patient_id: str
    file_name: str
    file_path: str
    extracted_text: Optional[str] = None
    extracted_labs: List[ExtractedLab] = []
    uploaded_at: datetime

    class Config:
        from_attributes = True
