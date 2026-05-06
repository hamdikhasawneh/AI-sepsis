from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.lab_result import LabResult
from app.schemas.lab_result import LabResultCreate, LabResultResponse

from app.dependencies.auth import get_current_user, require_role
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[LabResultResponse])
def get_labs(patient_id: str = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(LabResult)
    if patient_id:
        query = query.filter(LabResult.patient_id == patient_id)
    return query.all()

@router.post("/", response_model=LabResultResponse)
def create_lab(lab: LabResultCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "nurse"))):
    db_lab = LabResult(**lab.model_dump())
    db.add(db_lab)
    db.commit()
    db.refresh(db_lab)
    return db_lab
