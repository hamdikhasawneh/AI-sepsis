from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import bcrypt

from database import get_db
import models
import schemas

app = FastAPI(title="AI Sepsis Backend")

@app.get("/")
def root():
    return {"message": "Backend is running"}

@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not bcrypt.checkpw(user.password.encode(), db_user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Wrong password")

    return {
        "message": "Login successful",
        "user_id": db_user.user_id,
        "role": db_user.role
    }

@app.get("/patients")
def get_patients(db: Session = Depends(get_db)):
    return db.query(models.Patient).all()

@app.post("/patients")
def add_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    new_patient = models.Patient(
        full_name=patient.full_name,
        status=patient.status,
        assigned_doctor_id=patient.assigned_doctor_id
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient

@app.post("/vitals")
def add_vital(vital: schemas.VitalCreate, db: Session = Depends(get_db)):
    new_vital = models.VitalSigns(**vital.model_dump())
    db.add(new_vital)
    db.commit()
    db.refresh(new_vital)
    return {"message": "Vital added", "vital_id": new_vital.vital_id}

@app.post("/labs")
def add_lab(lab: schemas.LabCreate, db: Session = Depends(get_db)):
    new_lab = models.LabResult(**lab.model_dump())
    db.add(new_lab)
    db.commit()
    db.refresh(new_lab)
    return {"message": "Lab result added", "lab_id": new_lab.lab_id}

@app.get("/alerts/{patient_id}")
def get_alerts(patient_id: int, db: Session = Depends(get_db)):
    return db.query(models.Alert).filter(models.Alert.patient_id == patient_id).all()
