import random
from datetime import datetime, timedelta, timezone, date
from app.db.session import SessionLocal
from app.models.user import User
from app.models.patient import Patient
from app.models.vital_signs import VitalSign
from app.models.prediction import Prediction
from app.models.alert import Alert
from app.models.system_setting import SystemSetting
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

        print("[Seed] Seeding database with demo data...")

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

        # ─── Patients ───
        patients_data = [
            {"full_name": "Ahmad Al-Hassan", "age": 65, "gender": "male",
             "bed_number": "ICU-01", "ward_name": "ICU", "status": "admitted",
             "assigned_doctor_id": doctor1.user_id, "date_of_birth": date(1961, 3, 15),
             "diagnosis_notes": "Suspected sepsis secondary to pneumonia"},
            {"full_name": "Fatima Khalil", "age": 72, "gender": "female",
             "bed_number": "ICU-02", "ward_name": "ICU", "status": "admitted",
             "assigned_doctor_id": doctor1.user_id, "date_of_birth": date(1954, 7, 22),
             "diagnosis_notes": "Post-surgical monitoring, abdominal infection"},
            {"full_name": "Omar Nasser", "age": 45, "gender": "male",
             "bed_number": "ICU-03", "ward_name": "ICU", "status": "admitted",
             "assigned_doctor_id": doctor2.user_id, "date_of_birth": date(1981, 11, 4),
             "diagnosis_notes": "UTI progressing to urosepsis"},
            {"full_name": "Sara Mohammed", "age": 58, "gender": "female",
             "bed_number": "ICU-04", "ward_name": "ICU", "status": "admitted",
             "assigned_doctor_id": doctor2.user_id, "date_of_birth": date(1968, 1, 30),
             "diagnosis_notes": "Community-acquired pneumonia with sepsis risk"},
            {"full_name": "Khaled Ibrahim", "age": 80, "gender": "male",
             "bed_number": "ICU-05", "ward_name": "ICU", "status": "admitted",
             "assigned_doctor_id": doctor1.user_id, "date_of_birth": date(1946, 5, 12),
             "diagnosis_notes": "Multiorgan monitoring, advanced age"},
            {"full_name": "Layla Abdallah", "age": 34, "gender": "female",
             "bed_number": "ICU-06", "ward_name": "ICU", "status": "admitted",
             "assigned_doctor_id": doctor2.user_id, "date_of_birth": date(1992, 9, 8),
             "diagnosis_notes": "Appendicitis post-op, monitoring for peritonitis"},
            {"full_name": "Youssef Haddad", "age": 55, "gender": "male",
             "bed_number": "ICU-07", "ward_name": "ICU", "status": "admitted",
             "assigned_doctor_id": doctor1.user_id, "date_of_birth": date(1971, 6, 18),
             "diagnosis_notes": "Acute respiratory distress"},
            {"full_name": "Nour Kassem", "age": 68, "gender": "female",
             "bed_number": "ICU-08", "ward_name": "ICU", "status": "admitted",
             "assigned_doctor_id": doctor2.user_id, "date_of_birth": date(1958, 2, 25),
             "diagnosis_notes": "Diabetic foot infection, sepsis watch"},
            # History patients
            {"full_name": "Rami Saleh", "age": 42, "gender": "male",
             "bed_number": "ICU-09", "ward_name": "ICU", "status": "discharged",
             "assigned_doctor_id": doctor1.user_id, "date_of_birth": date(1984, 4, 10),
             "diagnosis_notes": "Recovered from septic shock",
             "discharge_time": datetime.now(timezone.utc) - timedelta(days=3)},
            {"full_name": "Dina Mansour", "age": 60, "gender": "female",
             "bed_number": "ICU-10", "ward_name": "ICU", "status": "transferred",
             "assigned_doctor_id": doctor2.user_id, "date_of_birth": date(1966, 8, 14),
             "diagnosis_notes": "Transferred to general ward, stable",
             "discharge_time": datetime.now(timezone.utc) - timedelta(days=1)},
            {"full_name": "Hassan Barakat", "age": 75, "gender": "male",
             "bed_number": "ICU-11", "ward_name": "ICU", "status": "discharged",
             "assigned_doctor_id": doctor1.user_id, "date_of_birth": date(1951, 12, 3),
             "diagnosis_notes": "Full recovery, no further ICU care needed",
             "discharge_time": datetime.now(timezone.utc) - timedelta(days=5)},
            {"full_name": "Mira Tawfik", "age": 29, "gender": "female",
             "bed_number": "ICU-12", "ward_name": "ICU", "status": "transferred",
             "assigned_doctor_id": doctor2.user_id, "date_of_birth": date(1997, 10, 20),
             "diagnosis_notes": "Stable, moved to step-down unit",
             "discharge_time": datetime.now(timezone.utc) - timedelta(days=2)},
        ]

        patient_objects = []
        for p_data in patients_data:
            discharge_time = p_data.pop("discharge_time", None)
            admission_offset = random.randint(1, 7)
            patient = Patient(
                **p_data,
                admission_time=datetime.now(timezone.utc) - timedelta(days=admission_offset),
                discharge_time=discharge_time,
                created_by_user_id=nurse1.user_id,
            )
            patient_objects.append(patient)

        db.add_all(patient_objects)
        db.flush()

        # ─── Sample Vital Signs ── for admitted patients
        for patient in patient_objects:
            if patient.status != "admitted":
                continue
            for i in range(24):
                timestamp = datetime.now(timezone.utc) - timedelta(minutes=30 * i)
                vital = VitalSign(
                    patient_id=patient.patient_id,
                    recorded_at=timestamp,
                    heart_rate=round(random.uniform(60, 120), 1),
                    respiratory_rate=round(random.uniform(12, 30), 1),
                    temperature=round(random.uniform(36.0, 39.5), 1),
                    spo2=round(random.uniform(90, 100), 1),
                    systolic_bp=round(random.uniform(90, 160), 1),
                    diastolic_bp=round(random.uniform(50, 100), 1),
                    mean_bp=round(random.uniform(65, 120), 1),
                    source="monitor",
                )
                db.add(vital)
        db.flush()

        # ─── Sample Predictions ── for admitted patients
        prediction_count = 0
        for patient in patient_objects:
            if patient.status != "admitted":
                continue
            for i in range(6):
                timestamp = datetime.now(timezone.utc) - timedelta(hours=2 * i)
                risk_score = round(random.uniform(0.1, 0.95), 4)
                risk_level = "critical" if risk_score >= 0.9 else "high" if risk_score >= 0.8 else "medium" if risk_score >= 0.48 else "low"
                pred = Prediction(
                    patient_id=patient.patient_id,
                    predicted_at=timestamp,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    threshold_used=0.80,
                    model_version="mock-v1",
                    input_window_hours=6,
                )
                db.add(pred)
                prediction_count += 1
        db.flush()

        # ─── Sample Alerts ── for some high-risk patients
        alert_count = 0
        # Create alerts for the first 3 admitted patients
        for patient in patient_objects[:3]:
            latest_pred = (
                db.query(Prediction)
                .filter(Prediction.patient_id == patient.patient_id)
                .order_by(Prediction.predicted_at.desc())
                .first()
            )
            if latest_pred:
                alert = Alert(
                    prediction_id=latest_pred.prediction_id,
                    patient_id=patient.patient_id,
                    alert_message=f"⚠️ High sepsis risk detected for {patient.full_name}. "
                                  f"Risk score: {latest_pred.risk_score:.2%} (threshold: 80.00%)",
                    alert_level="high" if latest_pred.risk_score < 0.9 else "critical",
                    is_read=False,
                )
                db.add(alert)
                alert_count += 1

        # Create a read alert for patient 4
        if len(patient_objects) > 3:
            pred4 = (
                db.query(Prediction)
                .filter(Prediction.patient_id == patient_objects[3].patient_id)
                .order_by(Prediction.predicted_at.desc())
                .first()
            )
            if pred4:
                read_alert = Alert(
                    prediction_id=pred4.prediction_id,
                    patient_id=patient_objects[3].patient_id,
                    alert_message=f"⚠️ High sepsis risk detected for {patient_objects[3].full_name}. "
                                  f"Risk score: {pred4.risk_score:.2%} (threshold: 80.00%)",
                    alert_level="high",
                    is_read=True,
                    read_by_user_id=doctor2.user_id,
                    read_at=datetime.now(timezone.utc) - timedelta(hours=1),
                )
                db.add(read_alert)
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
        print("[Seed] ✓ Database seeded successfully!")
        print(f"[Seed]   Users: 5 (1 admin, 2 doctors, 2 nurses)")
        print(f"[Seed]   Patients: {len(patient_objects)} (8 admitted, 4 history)")
        print(f"[Seed]   Predictions: {prediction_count}")
        print(f"[Seed]   Alerts: {alert_count}")
        print(f"[Seed]   System settings: 2")

    except Exception as e:
        db.rollback()
        print(f"[Seed] Error seeding database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
