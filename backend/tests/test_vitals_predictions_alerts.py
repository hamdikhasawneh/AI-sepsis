"""Tests for vitals ingestion, prediction pipeline, and alert engine."""

from datetime import datetime, timedelta, timezone
from tests.conftest import get_auth_header
from app.models.vital_signs import VitalSign
from app.models.prediction import Prediction
from app.models.alert import Alert
from app.services.prediction_service import (
    MockPredictorService, run_prediction_for_patient, get_risk_level
)
from app.services.alert_service import check_and_create_alert, get_unread_alert_count


class TestVitalsAPI:
    """Test vital sign ingestion."""

    def test_nurse_can_add_vital(self, client, nurse_user, sample_patient):
        headers = get_auth_header(client, "testnurse", "nurse123")
        resp = client.post("/api/vitals/", headers=headers, json={
            "patient_id": sample_patient.patient_id,
            "heart_rate": 85.0,
            "respiratory_rate": 18.0,
            "temperature": 37.0,
            "spo2": 98.0,
            "systolic_bp": 120.0,
            "diastolic_bp": 80.0,
            "mean_bp": 93.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["heart_rate"] == 85.0
        assert data["source"] == "manual"

    def test_doctor_cannot_add_vital(self, client, doctor_user, sample_patient):
        headers = get_auth_header(client, "testdoctor", "doctor123")
        resp = client.post("/api/vitals/", headers=headers, json={
            "patient_id": sample_patient.patient_id,
            "heart_rate": 85.0,
        })
        assert resp.status_code == 403

    def test_get_patient_vitals(self, client, admin_user, sample_patient, db):
        # Add a vital directly
        vital = VitalSign(
            patient_id=sample_patient.patient_id,
            heart_rate=90.0,
            respiratory_rate=20.0,
            temperature=37.5,
            spo2=96.0,
            systolic_bp=115.0,
            diastolic_bp=75.0,
            mean_bp=88.0,
            source="monitor",
            recorded_at=datetime.now(timezone.utc),
        )
        db.add(vital)
        db.commit()

        headers = get_auth_header(client, "testadmin", "admin123")
        resp = client.get(
            f"/api/vitals/{sample_patient.patient_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestPredictionService:
    """Test the mock prediction service."""

    def test_mock_predictor_returns_valid_score(self):
        predictor = MockPredictorService()
        vitals = [
            {"heart_rate": 90, "respiratory_rate": 18, "temperature": 37.0,
             "spo2": 98, "systolic_bp": 120, "diastolic_bp": 80, "mean_bp": 93},
        ]
        score = predictor.predict(vitals)
        assert 0.0 <= score <= 1.0

    def test_high_risk_vitals_produce_higher_score(self):
        predictor = MockPredictorService()
        # Normal vitals
        normal = [{"heart_rate": 75, "respiratory_rate": 16, "temperature": 37.0,
                    "spo2": 98, "systolic_bp": 120, "diastolic_bp": 80, "mean_bp": 93}]
        # Abnormal vitals (high HR, fever, low SpO2, low BP)
        abnormal = [{"heart_rate": 115, "respiratory_rate": 28, "temperature": 39.5,
                      "spo2": 88, "systolic_bp": 85, "diastolic_bp": 55, "mean_bp": 65}]

        normal_score = predictor.predict(normal)
        abnormal_score = predictor.predict(abnormal)

        # Abnormal should generally score higher (though randomness means we can't guarantee)
        # Run multiple times to reduce flakiness
        normal_avg = sum(predictor.predict(normal) for _ in range(10)) / 10
        abnormal_avg = sum(predictor.predict(abnormal) for _ in range(10)) / 10
        assert abnormal_avg > normal_avg

    def test_risk_level_mapping(self):
        assert get_risk_level(0.95, 0.80) == "critical"
        assert get_risk_level(0.85, 0.80) == "high"
        assert get_risk_level(0.55, 0.80) == "medium"
        assert get_risk_level(0.30, 0.80) == "low"

    def test_empty_vitals_returns_low_score(self):
        predictor = MockPredictorService()
        score = predictor.predict([])
        assert 0.0 <= score <= 0.5

    def test_run_prediction_for_patient(self, db, sample_patient, threshold_setting):
        # Add enough vitals
        for i in range(5):
            vital = VitalSign(
                patient_id=sample_patient.patient_id,
                heart_rate=85 + i * 2,
                respiratory_rate=18,
                temperature=37.0,
                spo2=96,
                systolic_bp=120,
                diastolic_bp=80,
                mean_bp=93,
                source="monitor",
                recorded_at=datetime.now(timezone.utc) - timedelta(hours=i),
            )
            db.add(vital)
        db.commit()

        prediction = run_prediction_for_patient(db, sample_patient.patient_id)
        assert prediction is not None
        assert 0.0 <= prediction.risk_score <= 1.0
        assert prediction.model_version == "mock-v1"
        assert prediction.input_window_hours == 6

    def test_prediction_needs_minimum_vitals(self, db, sample_patient, threshold_setting):
        # Only 1 vital — not enough
        vital = VitalSign(
            patient_id=sample_patient.patient_id,
            heart_rate=90,
            recorded_at=datetime.now(timezone.utc),
            source="monitor",
        )
        db.add(vital)
        db.commit()

        prediction = run_prediction_for_patient(db, sample_patient.patient_id)
        assert prediction is None  # Not enough data


class TestAlertEngine:
    """Test alert creation, thresholds, and duplicate prevention."""

    def _create_prediction(self, db, patient_id, risk_score):
        pred = Prediction(
            patient_id=patient_id,
            risk_score=risk_score,
            risk_level="high" if risk_score >= 0.8 else "low",
            threshold_used=0.80,
            model_version="mock-v1",
            predicted_at=datetime.now(timezone.utc),
        )
        db.add(pred)
        db.commit()
        db.refresh(pred)
        return pred

    def test_alert_created_for_high_risk(self, db, sample_patient, threshold_setting):
        pred = self._create_prediction(db, sample_patient.patient_id, 0.90)
        alert = check_and_create_alert(db, pred)
        assert alert is not None
        assert alert.is_read is False
        assert "risk" in alert.alert_message.lower()

    def test_no_alert_for_low_risk(self, db, sample_patient, threshold_setting):
        pred = self._create_prediction(db, sample_patient.patient_id, 0.30)
        alert = check_and_create_alert(db, pred)
        assert alert is None

    def test_no_duplicate_unread_alert(self, db, sample_patient, threshold_setting):
        # First alert should be created
        pred1 = self._create_prediction(db, sample_patient.patient_id, 0.90)
        alert1 = check_and_create_alert(db, pred1)
        assert alert1 is not None

        # Second alert should be prevented (duplicate unread)
        pred2 = self._create_prediction(db, sample_patient.patient_id, 0.92)
        alert2 = check_and_create_alert(db, pred2)
        assert alert2 is None

    def test_new_alert_after_reading(self, db, sample_patient, threshold_setting, doctor_user):
        # Create and read first alert
        pred1 = self._create_prediction(db, sample_patient.patient_id, 0.90)
        alert1 = check_and_create_alert(db, pred1)
        assert alert1 is not None

        # Mark as read
        alert1.is_read = True
        alert1.read_by_user_id = doctor_user.user_id
        db.commit()

        # Now a new alert should be created
        pred2 = self._create_prediction(db, sample_patient.patient_id, 0.88)
        alert2 = check_and_create_alert(db, pred2)
        assert alert2 is not None

    def test_unread_count(self, db, sample_patient, threshold_setting):
        pred = self._create_prediction(db, sample_patient.patient_id, 0.90)
        check_and_create_alert(db, pred)

        count = get_unread_alert_count(db)
        assert count >= 1


class TestAlertAPI:
    """Test alert API endpoints."""

    def test_list_alerts(self, client, admin_user):
        headers = get_auth_header(client, "testadmin", "admin123")
        resp = client.get("/api/alerts/", headers=headers)
        assert resp.status_code == 200

    def test_unread_count_endpoint(self, client, admin_user):
        headers = get_auth_header(client, "testadmin", "admin123")
        resp = client.get("/api/alerts/unread/count", headers=headers)
        assert resp.status_code == 200
        assert "unread_count" in resp.json()

    def test_doctor_can_mark_read(self, client, doctor_user, db, sample_patient, threshold_setting):
        # Create an alert
        pred = Prediction(
            patient_id=sample_patient.patient_id,
            risk_score=0.90,
            risk_level="high",
            threshold_used=0.80,
            predicted_at=datetime.now(timezone.utc),
        )
        db.add(pred)
        db.commit()
        db.refresh(pred)

        alert = Alert(
            prediction_id=pred.prediction_id,
            patient_id=sample_patient.patient_id,
            alert_message="Test alert",
            alert_level="high",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        headers = get_auth_header(client, "testdoctor", "doctor123")
        resp = client.patch(f"/api/alerts/{alert.alert_id}/read", headers=headers)
        assert resp.status_code == 200

    def test_nurse_cannot_mark_read(self, client, nurse_user, db, sample_patient, threshold_setting):
        pred = Prediction(
            patient_id=sample_patient.patient_id,
            risk_score=0.90,
            risk_level="high",
            threshold_used=0.80,
            predicted_at=datetime.now(timezone.utc),
        )
        db.add(pred)
        db.commit()
        db.refresh(pred)

        alert = Alert(
            prediction_id=pred.prediction_id,
            patient_id=sample_patient.patient_id,
            alert_message="Test alert",
            alert_level="high",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        headers = get_auth_header(client, "testnurse", "nurse123")
        resp = client.patch(f"/api/alerts/{alert.alert_id}/read", headers=headers)
        assert resp.status_code == 403
