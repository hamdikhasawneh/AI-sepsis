from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.lab_result import LabResult
from app.schemas.lab_result import LabResultCreate, LabResultResponse

router = APIRouter()

@router.get("/", response_model=List[LabResultResponse])
def get_labs(patient_id: str = None, db: Session = Depends(get_db)):
    query = db.query(LabResult)
    if patient_id:
        query = query.filter(LabResult.patient_id == patient_id)
    return query.all()

@router.post("/", response_model=LabResultResponse)
def create_lab(lab: LabResultCreate, db: Session = Depends(get_db)):
    db_lab = LabResult(**lab.model_dump())
    db.add(db_lab)
    db.commit()
    db.refresh(db_lab)
    return db_lab
