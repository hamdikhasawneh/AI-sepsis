import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone, date
from app.db.session import SessionLocal
from app.models.user import User
from app.models.patient import Patient
from app.models.vital_signs import VitalSign
from app.models.prediction import Prediction
from app.models.alert import Alert
from app.models.system_setting import SystemSetting
from app.models.lab_result import LabResult
from app.core.security import hash_password


def seed_data():
    """Seed the database with demo data if empty."""
    db = SessionLocal()

    try:
        # Check if already seeded
        existing_users = db.query(User).count()
        if existing_users > 0:
            print("[Seed] Database already has data, skipping seed.")
            return

        print("[Seed] Seeding database with real clinical data...")

        # ─── Users ───
        admin = User(
            username="admin",
            email="admin@sepsis.icu",
            password_hash=hash_password("admin123"),
            full_name="System Admin",
            role="admin",
        )
        doctor1 = User(
            username="dr.smith",
            email="smith@sepsis.icu",
            password_hash=hash_password("doctor123"),
            full_name="Dr. John Smith",
            role="doctor",
        )
        doctor2 = User(
            username="dr.johnson",
            email="johnson@sepsis.icu",
            password_hash=hash_password("doctor123"),
            full_name="Dr. Sarah Johnson",
            role="doctor",
        )
        nurse1 = User(
            username="nurse.jane",
            email="jane@sepsis.icu",
            password_hash=hash_password("nurse123"),
            full_name="Jane Williams",
            role="nurse",
        )
        nurse2 = User(
            username="nurse.mike",
            email="mike@sepsis.icu",
            password_hash=hash_password("nurse123"),
            full_name="Mike Thompson",
            role="nurse",
        )

        db.add_all([admin, doctor1, doctor2, nurse1, nurse2])
        db.flush()

        # ─── Load Real Data ───
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        DATA_DIR = os.path.join(BASE_DIR, "data")
        
        cohort_path = os.path.join(DATA_DIR, "icu_cohort (1).csv")
        vitals_path = os.path.join(DATA_DIR, "vitals_complete.csv")
        labels_path = os.path.join(DATA_DIR, "hourly_labels.csv")
        labs_path = os.path.join(DATA_DIR, "patient_labs.csv")

        print(f"[Seed] Loading CSV data from {DATA_DIR}...")
        cohort = pd.read_csv(cohort_path)
        labels = pd.read_csv(labels_path)
        vitals = pd.read_csv(vitals_path)
        labs_df = pd.read_csv(labs_path) if os.path.exists(labs_path) else pd.DataFrame()

        # Sample up to 50 patients: 25 sepsis, 25 control
        # Only use patients with more than one reading
        np.random.seed(42) # For reproducibility
        stay_counts = labels['stay_id'].value_counts()
        longitudinal_stay_ids = set(stay_counts[stay_counts > 1].index)
        
        all_sepsis_stay_ids = labels[labels['label'] == 1]['stay_id'].unique()
        sepsis_stay_ids = [sid for sid in all_sepsis_stay_ids if sid in longitudinal_stay_ids]
        
        all_control_stay_ids = labels[~labels['stay_id'].isin(all_sepsis_stay_ids)]['stay_id'].unique()
        control_stay_ids = [sid for sid in all_control_stay_ids if sid in longitudinal_stay_ids]

        print(f"[Seed] Found {len(sepsis_stay_ids)} longitudinal sepsis patients and {len(control_stay_ids)} longitudinal control patients.")

        sampled_sepsis = np.random.choice(sepsis_stay_ids, min(25, len(sepsis_stay_ids)), replace=False)
        sampled_control = np.random.choice(control_stay_ids, min(25, len(control_stay_ids)), replace=False)
        selected_stay_ids = np.concatenate([sampled_sepsis, sampled_control])

        cohort_sample = cohort[cohort['stay_id'].isin(selected_stay_ids)]
        labels_sample = labels[labels['stay_id'].isin(selected_stay_ids)].copy()
        vitals_sample = vitals[vitals['stay_id'].isin(selected_stay_ids)].copy()
        labs_sample = labs_df[labs_df['stay_id'].isin(selected_stay_ids)].copy() if not labs_df.empty else pd.DataFrame()

        # Parse times in labels
        labels_sample['abs_time'] = pd.to_datetime(labels_sample['abs_time']).dt.tz_localize(timezone.utc)

        # ─── Patients ───
        patient_objects = []
        now = datetime.now(timezone.utc)

        # We will make most admitted, a few discharged.
        admitted_stay_ids = selected_stay_ids[:40]

        for _, row in cohort_sample.iterrows():
            stay_id = row['stay_id']
            
            # Find max time for this patient in labels to compute offset
            patient_labels = labels_sample[labels_sample['stay_id'] == stay_id]
            if patient_labels.empty:
                continue
                
            max_time = patient_labels['abs_time'].max()
            
            # If admitted, max_time becomes now. If discharged, max_time becomes now - random(1, 5) days.
            if stay_id in admitted_stay_ids:
                offset = now - max_time
                status = "admitted"
                discharge_time = None
            else:
                days_ago = random.randint(1, 5)
                target_time = now - timedelta(days=days_ago)
                offset = target_time - max_time
                status = random.choice(["discharged", "transferred"])
                discharge_time = target_time

            # Shift the labels for this patient
            labels_sample.loc[labels_sample['stay_id'] == stay_id, 'shifted_time'] = patient_labels['abs_time'] + offset
            
            # We will use this offset for vitals as well, mapping by 'hour'
            
            # Create Patient object
            age = int(row['anchor_age'])
            try:
                date_of_birth = date(now.year - age, 1, 1)
            except ValueError:
                date_of_birth = date(1900, 1, 1)
                
            doctor = random.choice([doctor1, doctor2])
            
            patient = Patient(
                full_name=f"Patient {row['subject_id']}",
                age=age,
                gender="male" if row['gender'] == "M" else "female",
                bed_number=f"ICU-{str(stay_id)[-4:]}",
                ward_name=str(row['first_careunit']),
                status=status,
                assigned_doctor_id=doctor.user_id,
                date_of_birth=date_of_birth,
                diagnosis_notes=f"Admission type: {row['admission_type']}",
                admission_time=patient_labels['abs_time'].min() + offset,
                discharge_time=discharge_time,
                created_by_user_id=random.choice([nurse1, nurse2]).user_id,
            )
            # Store the generated ID mapping
            patient._stay_id = stay_id
            patient_objects.append(patient)

        db.add_all(patient_objects)
        db.flush()

        # ─── Vitals ───
        vital_objects = []
        for p in patient_objects:
            p_labels = labels_sample[labels_sample['stay_id'] == p._stay_id]
            p_vitals = vitals_sample[vitals_sample['stay_id'] == p._stay_id]
            
            # Map hour to shifted_time
            hour_to_time = dict(zip(p_labels['hour'], p_labels['shifted_time']))
            
            for _, v_row in p_vitals.iterrows():
                hour = v_row['hour']
                if hour not in hour_to_time:
                    continue
                
                v_time = hour_to_time[hour]
                if pd.isna(v_time):
                    continue
                    
                vital = VitalSign(
                    patient_id=p.patient_id,
                    recorded_at=v_time.to_pydatetime(),
                    heart_rate=float(v_row['heart_rate']) if not pd.isna(v_row['heart_rate']) else None,
                    respiratory_rate=float(v_row['resp_rate']) if not pd.isna(v_row['resp_rate']) else None,
                    temperature=float(v_row['temp_c']) if not pd.isna(v_row['temp_c']) else None,
                    spo2=float(v_row['spo2']) if not pd.isna(v_row['spo2']) else None,
                    systolic_bp=float(v_row['abp_sys']) if not pd.isna(v_row['abp_sys']) else None,
                    diastolic_bp=float(v_row['abp_dia']) if not pd.isna(v_row['abp_dia']) else None,
                    mean_bp=float(v_row['abp_mean']) if not pd.isna(v_row['abp_mean']) else None,
                    source="monitor",
                )
                vital_objects.append(vital)
                
        # Bulk insert vitals
        for i in range(0, len(vital_objects), 1000):
            db.add_all(vital_objects[i:i+1000])
        db.flush()
        
        # ─── Labs ───
        lab_objects = []
        if not labs_sample.empty:
            test_mapping = {
                'lactate': ('Lactate', 'mmol/L', '0.5-2.0'),
                'wbc': ('WBC', 'K/uL', '4.5-11.0'),
                'platelets_raw': ('Platelets', 'K/uL', '150-450'),
                'crp': ('CRP', 'mg/L', '<3.0'),
                'inr': ('INR', 'ratio', '0.8-1.2'),
                'urine_output': ('Urine Output', 'mL', '>0.5 mL/kg/hr'),
            }
            
            for p in patient_objects:
                p_labels = labels_sample[labels_sample['stay_id'] == p._stay_id]
                p_labs = labs_sample[labs_sample['stay_id'] == p._stay_id]
                
                hour_to_time = dict(zip(p_labels['hour'], p_labels['shifted_time']))
                
                for _, l_row in p_labs.iterrows():
                    hour = l_row['hour']
                    if hour not in hour_to_time:
                        continue
                    
                    l_time = hour_to_time[hour]
                    if pd.isna(l_time):
                        continue
                        
                    for col, (name, unit, ref) in test_mapping.items():
                        if col in l_row and not pd.isna(l_row[col]):
                            val = float(l_row[col])
                            
                            # Determine status very naively based on reference range
                            status = "normal"
                            try:
                                if '-' in ref:
                                    low, high = map(float, ref.split('-'))
                                    if val < low: status = "low"
                                    elif val > high: status = "high"
                                elif '<' in ref:
                                    high = float(ref.replace('<', ''))
                                    if val > high: status = "high"
                            except Exception:
                                pass
                                
                            lab = LabResult(
                                patient_id=p.patient_id,
                                test_name=name,
                                value=val,
                                unit=unit,
                                reference_range=ref,
                                status=status,
                                recorded_at=l_time.to_pydatetime()
                            )
                            lab_objects.append(lab)
            
            for i in range(0, len(lab_objects), 1000):
                db.add_all(lab_objects[i:i+1000])
            db.flush()
        
        # ─── Predictions ───
        prediction_objects = []
        for p in patient_objects:
            p_labels = labels_sample[labels_sample['stay_id'] == p._stay_id]
            
            for _, l_row in p_labels.iterrows():
                if pd.isna(l_row['shifted_time']):
                    continue
                    
                # We'll simulate a risk score based on the true label. 
                # If label=1, score is high.
                label = l_row['label']
                if label == 1:
                    risk_score = random.uniform(0.8, 0.99)
                else:
                    risk_score = random.uniform(0.1, 0.79)
                    
                risk_level = "critical" if risk_score >= 0.9 else "high" if risk_score >= 0.8 else "medium" if risk_score >= 0.48 else "low"
                
                pred = Prediction(
                    patient_id=p.patient_id,
                    predicted_at=l_row['shifted_time'].to_pydatetime(),
                    risk_score=risk_score,
                    risk_level=risk_level,
                    threshold_used=0.80,
                    model_version="Dynamic Survival Transformer",
                    input_window_hours=6,
                )
                prediction_objects.append(pred)
                
        for i in range(0, len(prediction_objects), 1000):
            db.add_all(prediction_objects[i:i+1000])
        db.flush()

        # ─── Alerts ───
        # Create alerts for some high-risk predictions of admitted patients
        alert_count = 0
        for p in patient_objects:
            if p.status != "admitted":
                continue
                
            # Get latest prediction
            latest_pred = (
                db.query(Prediction)
                .filter(Prediction.patient_id == p.patient_id)
                .order_by(Prediction.predicted_at.desc())
                .first()
            )
            
            if latest_pred and latest_pred.risk_score >= 0.8:
                # 90% chance the alert is unread, so it shows up in the UI
                is_read = random.random() < 0.1
                read_by = doctor1.user_id if is_read else None
                read_at = (datetime.now(timezone.utc) - timedelta(minutes=15)) if is_read else None
                
                alert = Alert(
                    prediction_id=latest_pred.prediction_id,
                    patient_id=p.patient_id,
                    alert_message=f"⚠️ High sepsis risk detected for {p.full_name}. "
                                  f"Risk score: {latest_pred.risk_score:.2%} (threshold: 80.00%)",
                    alert_level=latest_pred.risk_level,
                    is_read=is_read,
                    read_by_user_id=read_by,
                    read_at=read_at,
                )
                db.add(alert)
                alert_count += 1

        # ─── System Settings ───
        threshold_setting = SystemSetting(
            key="high_risk_threshold",
            value="0.80",
            updated_by_user_id=admin.user_id,
        )
        sound_setting = SystemSetting(
            key="sound_notifications",
            value="true",
            updated_by_user_id=admin.user_id,
        )
        db.add_all([threshold_setting, sound_setting])

        db.commit()
        print("[Seed] Database seeded successfully!")
        print(f"[Seed]   Users: 5 (1 admin, 2 doctors, 2 nurses)")
        print(f"[Seed]   Patients: {len(patient_objects)} ({len(admitted_stay_ids)} admitted, {len(patient_objects)-len(admitted_stay_ids)} history)")
        print(f"[Seed]   Vitals: {len(vital_objects)}")
        print(f"[Seed]   Predictions: {len(prediction_objects)}")
        print(f"[Seed]   Alerts: {alert_count}")
        print(f"[Seed]   System settings: 2")

    except Exception as e:
        db.rollback()
        print(f"[Seed] Error seeding database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

