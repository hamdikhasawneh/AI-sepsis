from pydantic import BaseModel
from datetime import datetime, date


class PatientCreate(BaseModel):
    full_name: str
    date_of_birth: date | None = None
    age: int | None = None
    gender: str | None = None
    bed_number: str | None = None
    ward_name: str | None = None
    status: str = "admitted"
    assigned_doctor_id: int | None = None
    diagnosis_notes: str | None = None


class PatientUpdate(BaseModel):
    full_name: str | None = None
    date_of_birth: date | None = None
    age: int | None = None
    gender: str | None = None
    bed_number: str | None = None
    ward_name: str | None = None
    status: str | None = None
    assigned_doctor_id: int | None = None
    diagnosis_notes: str | None = None
    discharge_time: datetime | None = None


class PatientNotesUpdate(BaseModel):
    diagnosis_notes: str


class PatientResponse(BaseModel):
    patient_id: int
    full_name: str
    date_of_birth: date | None = None
    age: int | None = None
    gender: str | None = None
    admission_time: datetime | None = None
    discharge_time: datetime | None = None
    bed_number: str | None = None
    ward_name: str | None = None
    status: str
    assigned_doctor_id: int | None = None
    diagnosis_notes: str | None = None
    created_by_user_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    doctor_name: str | None = None

    class Config:
        from_attributes = True
