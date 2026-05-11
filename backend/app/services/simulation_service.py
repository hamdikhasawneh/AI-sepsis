import pandas as pd
import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.patient import Patient
from app.models.vital_signs import VitalSign
from app.models.lab_result import LabResult
from app.services.prediction_service import run_prediction_for_patient
from app.services.alert_service import check_and_create_alert
from app.core.websocket import manager

from app.core.config import settings

logger = logging.getLogger(__name__)

class SimulationService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SimulationService, cls).__new__(cls)
            cls._instance.is_running = False
            cls._instance.current_case = None
            cls._instance.current_hour = 0
            cls._instance.hourly_data = None
            cls._instance.static_data = None
            cls._instance.task = None
            cls._instance.patient_id = 9999
        return cls._instance

    def load_data(self):
        if self.hourly_data is not None:
            return
        
        if not os.path.exists(settings.SIMULATION_EXCEL_PATH):
            logger.error(f"Simulation file not found at {settings.SIMULATION_EXCEL_PATH}")
            raise FileNotFoundError(f"Simulation file not found at {settings.SIMULATION_EXCEL_PATH}")

        try:
            logger.info("Loading simulation data from Excel...")
            # Use engine='openpyxl' explicitly to be sure
            self.hourly_data = pd.read_excel(settings.SIMULATION_EXCEL_PATH, sheet_name="Hourly_Sequence_25", header=1, engine='openpyxl')
            self.static_data = pd.read_excel(settings.SIMULATION_EXCEL_PATH, sheet_name="Static_Features_127", header=1, engine='openpyxl')
            
            # Basic validation
            if 'case_name' not in self.hourly_data.columns:
                logger.error(f"Missing 'case_name' in Hourly_Sequence_25. Columns: {self.hourly_data.columns}")
            if 'case_name' not in self.static_data.columns:
                logger.error(f"Missing 'case_name' in Static_Features_127. Columns: {self.static_data.columns}")
                
            logger.info("Simulation data loaded successfully.")
        except Exception as e:
            import traceback
            logger.error(f"Error loading simulation data: {e}\n{traceback.format_exc()}")
            raise e

    async def start(self, case_name: str):
        if self.is_running:
            return False
        
        self.load_data()
        if self.hourly_data is None:
            return False
            
        self.current_case = case_name
        self.current_hour = 0
        self.is_running = True
        
        # Start background task
        self.task = asyncio.create_task(self._run_simulation())
        return True

    def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()
            self.task = None
        self.current_case = None
        self.current_hour = 0

    def get_status(self):
        return {
            "running": self.is_running,
            "current_case": self.current_case,
            "current_hour": self.current_hour
        }

    async def _run_simulation(self):
        logger.info(f"Starting simulation loop for {self.current_case}")
        
        # Get case indices
        case_rows = self.hourly_data[self.hourly_data['case_name'] == self.current_case].sort_index()
        if case_rows.empty:
            logger.error(f"No data found for case {self.current_case}")
            self.stop()
            return

        # Prepare Patient in DB
        db = SessionLocal()
        try:
            static_row = self.static_data[self.static_data['case_name'] == self.current_case].iloc[0]
            patient = db.query(Patient).filter(Patient.full_name == f"Simulated Patient ({self.current_case})").first()
            if not patient:
                patient = Patient(
                    full_name=f"Simulated Patient ({self.current_case})",
                    age=int(static_row['anchor_age']),
                    gender="male" if static_row['gender_male'] == 1 else "female",
                    status="admitted",
                    bed_number="SIM-01",
                    ward_name="Simulation Lab"
                )
                db.add(patient)
            else:
                # Update status and ward name in case they were changed
                patient.status = "admitted"
                patient.ward_name = "Simulation Lab"
            
            db.commit()
            db.refresh(patient)
            self.patient_id = patient.patient_id
        finally:
            db.close()

        # Replay loop
        for idx, row in case_rows.iterrows():
            if not self.is_running:
                break
                
            self.current_hour += 1
            logger.info(f"Simulating hour {self.current_hour} for {self.current_case}")
            
            db = SessionLocal()
            try:
                # 1. Create Vital Signs
                vital = VitalSign(
                    patient_id=self.patient_id,
                    recorded_at=datetime.now(timezone.utc),
                    heart_rate=float(row['heart_rate']) if pd.notna(row['heart_rate']) else None,
                    respiratory_rate=float(row['resp_rate']) if pd.notna(row['resp_rate']) else None,
                    temperature=float(row['temp_c']) if pd.notna(row['temp_c']) else None,
                    spo2=float(row['spo2']) if pd.notna(row['spo2']) else None,
                    systolic_bp=float(row['abp_sys']) if pd.notna(row['abp_sys']) else None,
                    diastolic_bp=float(row['abp_dia']) if pd.notna(row['abp_dia']) else None,
                    mean_bp=float(row['abp_mean']) if pd.notna(row['abp_mean']) else None,
                    source="monitor"
                )
                db.add(vital)
                
                # 2. Create Lab Results (if any)
                labs_to_check = {
                    "lactate": ("mmol/L", "0.5-2.2"),
                    "wbc": ("10^3/uL", "4.0-11.0"),
                    "crp": ("mg/L", "0.0-5.0"),
                    "urine_output": ("ml/hr", "30-100")
                }
                
                for lab_name, (unit, ref) in labs_to_check.items():
                    if lab_name in row and pd.notna(row[lab_name]):
                        lab_res = LabResult(
                            patient_id=str(self.patient_id),
                            test_name=lab_name.upper(),
                            value=float(row[lab_name]),
                            unit=unit,
                            reference_range=ref,
                            status="final",
                            recorded_at=datetime.now(timezone.utc)
                        )
                        db.add(lab_res)

                db.commit()
                
                # 3. Trigger Prediction
                prediction = run_prediction_for_patient(db, self.patient_id)
                if prediction:
                    check_and_create_alert(db, prediction)
                    
                # 4. Notify UI via WebSocket (if needed, though polling might be easier)
                # For now, we rely on the UI polling or refreshing
                
            except Exception as e:
                logger.error(f"Error in simulation step: {e}")
            finally:
                db.close()
            
            await asyncio.sleep(3) # 1 hour = 3 seconds

        logger.info(f"Simulation for {self.current_case} finished.")
        self.stop()

# Global instance
simulation_service = SimulationService()
