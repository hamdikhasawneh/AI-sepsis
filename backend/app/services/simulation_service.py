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
            self.hourly_data = pd.read_excel(settings.SIMULATION_EXCEL_PATH, sheet_name="Hourly_Sequence_25", header=1, engine='openpyxl')
            # Try both possible static sheet names
            try:
                self.static_data = pd.read_excel(settings.SIMULATION_EXCEL_PATH, sheet_name="Static_Features_127", header=0, engine='openpyxl')
                logger.info("Loaded static sheet: Static_Features_127")
            except Exception:
                self.static_data = pd.read_excel(settings.SIMULATION_EXCEL_PATH, sheet_name="Static_Input_x_static", header=0, engine='openpyxl')
                logger.info("Loaded static sheet: Static_Input_x_static")
            
            if 'case_name' not in self.hourly_data.columns:
                logger.error(f"Missing 'case_name' in Hourly_Sequence_25. Columns: {self.hourly_data.columns.tolist()}")
            if 'case_name' not in self.static_data.columns:
                logger.error(f"Missing 'case_name' in static sheet. Columns: {self.static_data.columns.tolist()}")
                
            logger.info(f"Simulation data loaded. Cases: {self.hourly_data['case_name'].unique().tolist()}")
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
        
        self.task = asyncio.create_task(self._run_simulation())
        return True

    def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()
            self.task = None
        self.current_case = None
        self.current_hour = 0

    def clear(self, patient_id=None):
        self.stop()
        db = SessionLocal()
        try:
            if patient_id:
                db.query(Patient).filter(Patient.patient_id == patient_id).delete(synchronize_session=False)
                logger.info(f"Cleared simulation patient {patient_id} from the database.")
            else:
                db.query(Patient).filter(Patient.ward_name == "Simulation Lab").delete(synchronize_session=False)
                logger.info("Cleared all simulation patients from the database.")
            db.commit()
        except Exception as e:
            logger.error(f"Failed to clear simulation patients: {e}")
            db.rollback()
        finally:
            db.close()

    def get_status(self):
        return {
            "running": self.is_running,
            "current_case": self.current_case,
            "current_hour": self.current_hour
        }

    async def _run_simulation(self):
        logger.info(f"Starting simulation loop for {self.current_case}")
        
        case_rows = self.hourly_data[self.hourly_data['case_name'] == self.current_case].sort_index()
        if case_rows.empty:
            logger.error(f"No data found for case {self.current_case}")
            self.stop()
            return

        db = SessionLocal()
        try:
            static_row = self.static_data[self.static_data['case_name'] == self.current_case].iloc[0]
            
            patient = db.query(Patient).filter(Patient.full_name == f"Simulated Patient ({self.current_case})").first()
            if not patient:
                patient = Patient(
                    full_name=f"Simulated Patient ({self.current_case})",
                    age=int(static_row.get('anchor_age', 60)),
                    gender="male" if static_row.get('gender_male', 1) == 1 else "female",
                    status="admitted",
                    bed_number="SIM-01",
                    ward_name="Simulation Lab"
                )
                db.add(patient)
            else:
                patient.status = "admitted"
                patient.ward_name = "Simulation Lab"
            
            db.commit()
            db.refresh(patient)
            self.patient_id = patient.patient_id

            # ── Store full static feature dict on the patient for prediction service ──
            # Convert static row to plain dict for passing to predictor
            static_dict = static_row.to_dict()
            static_dict['age']    = int(static_row.get('anchor_age', 60))
            static_dict['gender'] = "male" if static_row.get('gender_male', 1) == 1 else "female"
            # Attach to patient object so run_prediction_for_patient can use it
            patient._simulation_static = static_dict

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
                # 1. Create Vital Signs — use MIMIC column names from Excel
                vital = VitalSign(
                    patient_id=self.patient_id,
                    recorded_at=datetime.now(timezone.utc),
                    heart_rate      =float(row['heart_rate'])  if pd.notna(row.get('heart_rate'))  else None,
                    respiratory_rate=float(row['resp_rate'])   if pd.notna(row.get('resp_rate'))   else None,
                    temperature     =float(row['temp_c'])      if pd.notna(row.get('temp_c'))      else None,
                    spo2            =float(row['spo2'])        if pd.notna(row.get('spo2'))        else None,
                    systolic_bp     =float(row['abp_sys'])     if pd.notna(row.get('abp_sys'))     else None,
                    diastolic_bp    =float(row['abp_dia'])     if pd.notna(row.get('abp_dia'))     else None,
                    mean_bp         =float(row['abp_mean'])    if pd.notna(row.get('abp_mean'))    else None,
                    source="monitor"
                )
                db.add(vital)

                # 2. Create Lab Results
                labs_to_check = {
                    "lactate":      ("mmol/L",  "0.5-2.2"),
                    "wbc":          ("10^3/uL", "4.0-11.0"),
                    "crp":          ("mg/L",    "0.0-5.0"),
                    "urine_output": ("ml/hr",   "30-100"),
                }
                for lab_name, (unit, ref) in labs_to_check.items():
                    val = row.get(lab_name)
                    if val is not None and pd.notna(val):
                        lab_res = LabResult(
                            patient_id=str(self.patient_id),
                            test_name=lab_name.upper(),
                            value=float(val),
                            unit=unit,
                            reference_range=ref,
                            status="final",
                            recorded_at=datetime.now(timezone.utc)
                        )
                        db.add(lab_res)

                db.commit()

                # 3. Build enriched vitals window with ALL features for prediction
                # Fetch all vitals stored so far (growing window)
                all_vitals = (
                    db.query(VitalSign)
                    .filter(VitalSign.patient_id == self.patient_id)
                    .order_by(VitalSign.recorded_at.asc())
                    .all()
                )

                # For each stored vital, attach the lab values from the Excel row
                # We replay from the hourly data so labs match the same hour
                hour_rows = case_rows.iloc[:self.current_hour]

                vitals_window = []
                for i, v in enumerate(all_vitals):
                    hr = hour_rows.iloc[i] if i < len(hour_rows) else hour_rows.iloc[-1]
                    vitals_window.append({
                        # Vital signs (both naming conventions for robustness)
                        "heart_rate":        v.heart_rate,
                        "respiratory_rate":  v.respiratory_rate,
                        "temperature":       v.temperature,
                        "spo2":              v.spo2,
                        "systolic_bp":       v.systolic_bp,
                        "diastolic_bp":      v.diastolic_bp,
                        "mean_bp":           v.mean_bp,
                        # Also MIMIC names for _preprocess_vitals fallback
                        "resp_rate":         v.respiratory_rate,
                        "temp_c":            v.temperature,
                        "abp_sys":           v.systolic_bp,
                        "abp_dia":           v.diastolic_bp,
                        "abp_mean":          v.mean_bp,
                        # Lab features from Excel row
                        "lactate":           float(hr.get('lactate', 1.5))         if pd.notna(hr.get('lactate'))         else 1.5,
                        "wbc":               float(hr.get('wbc', 8.0))             if pd.notna(hr.get('wbc'))             else 8.0,
                        "sofa_platelets":    float(hr.get('sofa_platelets', 0))    if pd.notna(hr.get('sofa_platelets'))  else 0,
                        "sofa_bilirubin":    float(hr.get('sofa_bilirubin', 0))    if pd.notna(hr.get('sofa_bilirubin'))  else 0,
                        "sofa_creatinine":   float(hr.get('sofa_creatinine', 0))   if pd.notna(hr.get('sofa_creatinine')) else 0,
                        "urine_output":      float(hr.get('urine_output', 60))     if pd.notna(hr.get('urine_output'))    else 60,
                        "vasopressor_flag":  float(hr.get('vasopressor_flag', 0))  if pd.notna(hr.get('vasopressor_flag'))else 0,
                        "crp":               float(hr.get('crp', 15))              if pd.notna(hr.get('crp'))             else 15,
                        "platelets_raw":     float(hr.get('platelets_raw', 200))   if pd.notna(hr.get('platelets_raw'))   else 200,
                        "inr":               float(hr.get('inr', 1.1))             if pd.notna(hr.get('inr'))             else 1.1,
                        "lactate_fresh":     float(hr.get('lactate_fresh', 0))     if pd.notna(hr.get('lactate_fresh'))   else 0,
                        "wbc_fresh":         float(hr.get('wbc_fresh', 0))         if pd.notna(hr.get('wbc_fresh'))       else 0,
                        "crp_fresh":         float(hr.get('crp_fresh', 0))         if pd.notna(hr.get('crp_fresh'))       else 0,
                        "platelets_fresh":   float(hr.get('platelets_fresh', 0))   if pd.notna(hr.get('platelets_fresh')) else 0,
                        "inr_fresh":         float(hr.get('inr_fresh', 0))         if pd.notna(hr.get('inr_fresh'))       else 0,
                    })

                # 4. Build full static dict from the Excel static row
                static_dict = self.static_data[
                    self.static_data['case_name'] == self.current_case
                ].iloc[0].to_dict()
                static_dict['age']    = int(static_dict.get('anchor_age', 60))
                static_dict['gender'] = "male" if static_dict.get('gender_male', 1) == 1 else "female"

                # 5. Run prediction with full feature vectors
                from app.services.prediction_service import get_predictor, get_threshold, get_risk_level, get_alert_tier
                from app.models.prediction import Prediction

                predictor  = get_predictor()
                risk_score = predictor.predict(vitals_window, static_dict)
                threshold  = get_threshold(db)
                risk_level = get_risk_level(risk_score, threshold)
                alert_tier = get_alert_tier(risk_score)

                logger.info(f"Hour {self.current_hour}: risk_score={risk_score:.4f} tier={alert_tier}")

                prediction = Prediction(
                    patient_id=self.patient_id,
                    predicted_at=datetime.now(timezone.utc),
                    risk_score=risk_score,
                    risk_level=risk_level,
                    threshold_used=threshold,
                    model_version="Dynamic Survival Transformer v2",
                    input_window_hours=len(vitals_window),
                )
                db.add(prediction)
                db.commit()
                db.refresh(prediction)

                check_and_create_alert(db, prediction)

            except Exception as e:
                import traceback
                logger.error(f"Error in simulation step hour {self.current_hour}: {e}\n{traceback.format_exc()}")
            finally:
                db.close()
            
            await asyncio.sleep(3)  # 1 hour = 3 seconds

        logger.info(f"Simulation for {self.current_case} finished.")
        self.stop()


# Global instance
simulation_service = SimulationService()
