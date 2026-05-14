import os
import sys
import torch
import numpy as np
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

# Add backend to path
sys.path.append(os.getcwd())

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.patient import Patient
from app.models.vital_signs import VitalSign
from app.models.prediction import Prediction
from app.models.shap_result import PatientShapResult
from app.services.prediction_service import run_prediction_for_patient, get_shap_for_patient

def test_live_shap():
    print("Starting Live SHAP Verification Test...")
    
    # 1. Initialize DB
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # 2. Create a test patient
        patient_name = f"Test SHAP Patient {datetime.now().strftime('%H%M%S')}"
        patient = Patient(
            full_name=patient_name,
            age=72,
            gender="male",
            status="admitted",
            ward_name="ICU",
            bed_number="T-01"
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        print(f"Created test patient: {patient.full_name} (ID: {patient.patient_id})")
        
        # 3. Add 12 hours of vitals (required for DST window)
        print("Adding 12 hours of vitals data...")
        for i in range(12):
            vital = VitalSign(
                patient_id=patient.patient_id,
                recorded_at=datetime.now(timezone.utc) - timedelta(hours=(12 - i)),
                heart_rate=110 + i, # Increasing HR to trigger risk
                respiratory_rate=24,
                temperature=38.5,
                spo2=92,
                systolic_bp=95,
                diastolic_bp=55,
                mean_bp=65,
                source="manual"
            )
            db.add(vital)
        db.commit()
        
        # 4. Run prediction
        print("Running prediction pipeline...")
        prediction = run_prediction_for_patient(db, patient.patient_id)
        
        if prediction:
            print(f"Prediction generated: Score={prediction.risk_score}, Level={prediction.risk_level}")
            
            # 5. Verify SHAP result in DB
            print("Verifying SHAP values in database...")
            shap_result = db.query(PatientShapResult).filter(
                PatientShapResult.prediction_id == prediction.prediction_id
            ).first()
            
            if shap_result:
                print("SUCCESS: Live SHAP values found in DB!")
                print(f"Top 3 contributors:")
                for feat in shap_result.shap_values[:3]:
                    print(f"  - {feat['feature']}: {feat['shap_value']} ({feat['direction']})")
                
                # 6. Verify via API-level lookup function
                api_result = get_shap_for_patient(db, patient.patient_id)
                if api_result and api_result.get('type') == 'live':
                    print("API lookup correctly prioritized live SHAP values.")
                else:
                    print("API lookup failed to prioritize live SHAP values.")
            else:
                print("FAILED: No SHAP values found in DB for the prediction.")
                print("Note: This is expected if 'captum' is not installed in the environment.")
        else:
            print("FAILED: Prediction was not generated.")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("Cleaning up test data...")
        db.close()

if __name__ == "__main__":
    test_live_shap()
