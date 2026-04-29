from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import os
import shutil
import uuid
from app.db.session import get_db
from app.models.document import Document
from app.schemas.document import DocumentResponse

router = APIRouter()

UPLOAD_DIR = "data/uploads"

@router.post("/upload", response_model=DocumentResponse)
def upload_document(
    patient_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    db_document = Document(
        patient_id=patient_id,
        file_name=file.filename,
        file_path=file_path
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    return db_document
