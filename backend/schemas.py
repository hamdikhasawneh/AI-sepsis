from pydantic import BaseModel

class UserLogin(BaseModel):
    username: str
    password: str

class VitalCreate(BaseModel):
    patient_id: int
    heart_rate: float
    respiratory_rate: float
    temperature: float
    spo2: float
    systolic_bp: float
    diastolic_bp: float
    mean_bp: float

class LabCreate(BaseModel):
    patient_id: int
    lab_name: str
    lab_value: float
    unit: str

class PatientCreate(BaseModel):
    full_name: str
    status: str
    assigned_doctor_id: int | None = None
