from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import os
import shutil
import uuid
import logging
from app.db.session import get_db
from app.models.document import Document
from app.models.lab_result import LabResult
from app.schemas.document import DocumentResponse
from app.services.ocr_service import process_pdf

router = APIRouter()
logger = logging.getLogger(__name__)

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
    
    # Save uploaded file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # ── OCR: Extract text and parse lab results from the PDF ──
    extracted_text = ""
    extracted_labs = []
    
    if file_extension.lower() == ".pdf":
        try:
            ocr_result = process_pdf(file_path)
            extracted_text = ocr_result["extracted_text"]
            extracted_labs = ocr_result["lab_results"]
            logger.info(
                "OCR extracted %d lab results from %s for patient %s",
                len(extracted_labs), file.filename, patient_id
            )
        except Exception as e:
            logger.error("OCR processing failed for %s: %s", file.filename, str(e))
            # Continue — the document is still saved even if OCR fails
    
    # Save the document record (with extracted text for audit)
    db_document = Document(
        patient_id=patient_id,
        file_name=file.filename,
        file_path=file_path,
        extracted_text=extracted_text if extracted_text else None
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    # ── Save each extracted lab result to the lab_results table ──
    for lab in extracted_labs:
        db_lab = LabResult(
            patient_id=patient_id,
            test_name=lab["test_name"],
            value=lab["value"],
            unit=lab["unit"],
            reference_range=lab["reference_range"],
            status=lab["status"]
        )
        db.add(db_lab)
    
    if extracted_labs:
        db.commit()
        logger.info(
            "Saved %d lab results to database for patient %s",
            len(extracted_labs), patient_id
        )
    
    # Build the response — attach extracted labs to the document response
    response = DocumentResponse(
        id=db_document.id,
        patient_id=db_document.patient_id,
        file_name=db_document.file_name,
        file_path=db_document.file_path,
        extracted_text=db_document.extracted_text,
        extracted_labs=extracted_labs,
        uploaded_at=db_document.uploaded_at
    )
    
    return response
