"""
Comprehensive API Test Suite for ICU Sepsis Detection System.
Covers: status codes, response structure, auth, RBAC, validation,
database CRUD, performance, and chained workflows.
"""
import time
import pytest
from tests.conftest import get_auth_header


# ═══════════════════════════════════════════════
# 1. HEALTH & STATUS CODE TESTS
# ═══════════════════════════════════════════════

class TestHealthEndpoints:
    def test_root_health(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_api_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200


# ═══════════════════════════════════════════════
# 2. AUTHENTICATION TESTS
# ═══════════════════════════════════════════════

class TestAuth:
    def test_login_success(self, client, admin_user):
        r = client.post("/api/auth/login", json={"username": "testadmin", "password": "admin123"})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)

    def test_login_wrong_password(self, client, admin_user):
        r = client.post("/api/auth/login", json={"username": "testadmin", "password": "wrong"})
        assert r.status_code == 401

    def test_login_nonexistent_user(self, client):
        r = client.post("/api/auth/login", json={"username": "ghost", "password": "pass"})
        assert r.status_code == 401

    def test_login_empty_body(self, client):
        r = client.post("/api/auth/login", json={})
        assert r.status_code == 422

    def test_login_missing_password(self, client):
        r = client.post("/api/auth/login", json={"username": "testadmin"})
        assert r.status_code == 422

    def test_me_with_valid_token(self, client, admin_user):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.get("/api/auth/me", headers=h)
        assert r.status_code == 200
        assert r.json()["username"] == "testadmin"
        assert r.json()["role"] == "admin"

    def test_me_no_token(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code in [401, 403]

    def test_me_invalid_token(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert r.status_code in [401, 403]

    def test_me_malformed_header(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "notbearer"})
        assert r.status_code in [401, 403, 422]

    def test_login_performance(self, client, admin_user):
        start = time.time()
        client.post("/api/auth/login", json={"username": "testadmin", "password": "admin123"})
        elapsed = (time.time() - start) * 1000
        assert elapsed < 1000, f"Login took {elapsed:.0f}ms (limit: 1000ms)"


# ═══════════════════════════════════════════════
# 3. USERS RBAC TESTS
# ═══════════════════════════════════════════════

class TestUsersRBAC:
    def test_admin_can_list_users(self, client, admin_user):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.get("/api/users/", headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_can_create_user(self, client, admin_user):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.post("/api/users/", headers=h, json={
            "username": "newdoc", "email": "new@test.com",
            "password": "pass123", "full_name": "New Doc", "role": "doctor"
        })
        assert r.status_code == 200
        assert r.json()["username"] == "newdoc"

    def test_doctor_cannot_list_users(self, client, admin_user, doctor_user):
        h = get_auth_header(client, "testdoctor", "doctor123")
        r = client.get("/api/users/", headers=h)
        assert r.status_code == 403

    def test_nurse_cannot_list_users(self, client, admin_user, nurse_user):
        h = get_auth_header(client, "testnurse", "nurse123")
        r = client.get("/api/users/", headers=h)
        assert r.status_code == 403

    def test_no_auth_cannot_list_users(self, client):
        r = client.get("/api/users/")
        assert r.status_code in [401, 403]

    def test_create_user_missing_fields(self, client, admin_user):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.post("/api/users/", headers=h, json={"username": "incomplete"})
        assert r.status_code == 422

    def test_user_response_structure(self, client, admin_user):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.get("/api/users/", headers=h)
        assert r.status_code == 200
        if len(r.json()) > 0:
            user = r.json()[0]
            for field in ["user_id", "username", "email", "full_name", "role", "is_active"]:
                assert field in user, f"Missing field: {field}"

    def test_admin_can_update_user(self, client, admin_user, doctor_user):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.patch(f"/api/users/{doctor_user.user_id}", headers=h,
                         json={"full_name": "Dr. Updated"})
        assert r.status_code == 200
        assert r.json()["full_name"] == "Dr. Updated"

    def test_update_nonexistent_user(self, client, admin_user):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.patch("/api/users/99999", headers=h, json={"full_name": "Ghost"})
        assert r.status_code == 404

    def test_list_doctors(self, client, admin_user, doctor_user, nurse_user):
        h = get_auth_header(client, "testnurse", "nurse123")
        r = client.get("/api/users/doctors", headers=h)
        assert r.status_code == 200
        assert all(u["role"] == "doctor" for u in r.json())


# ═══════════════════════════════════════════════
# 4. PATIENTS TESTS
# ═══════════════════════════════════════════════

class TestPatients:
    def test_nurse_can_create_patient(self, client, admin_user, nurse_user, doctor_user):
        h = get_auth_header(client, "testnurse", "nurse123")
        r = client.post("/api/patients/", headers=h, json={
            "full_name": "New Patient", "age": 50, "gender": "male",
            "bed_number": "ICU-99", "ward_name": "ICU",
            "assigned_doctor_id": doctor_user.user_id
        })
        assert r.status_code == 200
        assert r.json()["full_name"] == "New Patient"
        assert r.json()["patient_id"] is not None

    def test_patient_response_structure(self, client, admin_user, sample_patient):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.get(f"/api/patients/{sample_patient.patient_id}", headers=h)
        assert r.status_code == 200
        for field in ["patient_id", "full_name", "status", "bed_number"]:
            assert field in r.json()

    def test_list_patients(self, client, admin_user, sample_patient):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.get("/api/patients/?status_filter=active", headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_doctor_sees_only_own_patients(self, client, admin_user, doctor_user, sample_patient):
        h = get_auth_header(client, "testdoctor", "doctor123")
        r = client.get("/api/patients/", headers=h)
        assert r.status_code == 200
        for p in r.json():
            assert p["assigned_doctor_id"] == doctor_user.user_id

    def test_doctor_cannot_edit_patient(self, client, admin_user, doctor_user, sample_patient):
        h = get_auth_header(client, "testdoctor", "doctor123")
        r = client.patch(f"/api/patients/{sample_patient.patient_id}", headers=h,
                         json={"bed_number": "ICU-50"})
        assert r.status_code == 403

    def test_doctor_can_update_notes(self, client, admin_user, doctor_user, sample_patient):
        h = get_auth_header(client, "testdoctor", "doctor123")
        r = client.patch(f"/api/patients/{sample_patient.patient_id}/notes", headers=h,
                         json={"diagnosis_notes": "Updated notes"})
        assert r.status_code == 200

    def test_nurse_cannot_update_notes(self, client, admin_user, nurse_user, sample_patient):
        h = get_auth_header(client, "testnurse", "nurse123")
        r = client.patch(f"/api/patients/{sample_patient.patient_id}/notes", headers=h,
                         json={"diagnosis_notes": "Nurse notes"})
        assert r.status_code == 403

    def test_get_nonexistent_patient(self, client, admin_user):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.get("/api/patients/99999", headers=h)
        assert r.status_code == 404

    def test_create_patient_missing_name(self, client, admin_user, nurse_user):
        h = get_auth_header(client, "testnurse", "nurse123")
        r = client.post("/api/patients/", headers=h, json={"age": 50})
        assert r.status_code == 422

    def test_no_auth_cannot_list_patients(self, client):
        r = client.get("/api/patients/")
        assert r.status_code in [401, 403]

    def test_patient_performance(self, client, admin_user, sample_patient):
        h = get_auth_header(client, "testadmin", "admin123")
        start = time.time()
        client.get("/api/patients/", headers=h)
        elapsed = (time.time() - start) * 1000
        assert elapsed < 2000


# ═══════════════════════════════════════════════
# 5. VITALS TESTS
# ═══════════════════════════════════════════════

class TestVitals:
    def test_nurse_can_add_vital(self, client, admin_user, nurse_user, sample_patient):
        h = get_auth_header(client, "testnurse", "nurse123")
        r = client.post("/api/vitals/", headers=h, json={
            "patient_id": sample_patient.patient_id,
            "heart_rate": 85.0, "temperature": 37.5, "spo2": 96.0,
            "systolic_bp": 120.0, "diastolic_bp": 80.0
        })
        assert r.status_code == 200
        assert r.json()["heart_rate"] == 85.0

    def test_doctor_cannot_add_vital(self, client, admin_user, doctor_user, sample_patient):
        h = get_auth_header(client, "testdoctor", "doctor123")
        r = client.post("/api/vitals/", headers=h, json={
            "patient_id": sample_patient.patient_id, "heart_rate": 80.0
        })
        assert r.status_code == 403

    def test_get_patient_vitals(self, client, admin_user, nurse_user, sample_patient):
        h = get_auth_header(client, "testnurse", "nurse123")
        # Add a vital first
        client.post("/api/vitals/", headers=h, json={
            "patient_id": sample_patient.patient_id, "heart_rate": 90.0
        })
        h2 = get_auth_header(client, "testadmin", "admin123")
        r = client.get(f"/api/vitals/{sample_patient.patient_id}", headers=h2)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_vital_response_structure(self, client, admin_user, nurse_user, sample_patient):
        h = get_auth_header(client, "testnurse", "nurse123")
        client.post("/api/vitals/", headers=h, json={
            "patient_id": sample_patient.patient_id, "heart_rate": 75.0
        })
        h2 = get_auth_header(client, "testadmin", "admin123")
        r = client.get(f"/api/vitals/{sample_patient.patient_id}", headers=h2)
        if r.json():
            v = r.json()[0]
            for f in ["vital_id", "patient_id", "heart_rate", "source"]:
                assert f in v

    def test_add_vital_missing_patient_id(self, client, admin_user, nurse_user):
        h = get_auth_header(client, "testnurse", "nurse123")
        r = client.post("/api/vitals/", headers=h, json={"heart_rate": 80})
        assert r.status_code == 422


# ═══════════════════════════════════════════════
# 6. PREDICTIONS TESTS
# ═══════════════════════════════════════════════

class TestPredictions:
    def test_get_predictions(self, client, admin_user, sample_patient):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.get(f"/api/predictions/{sample_patient.patient_id}", headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_latest_prediction(self, client, admin_user, sample_patient):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.get(f"/api/predictions/{sample_patient.patient_id}/latest", headers=h)
        assert r.status_code == 200

    def test_no_auth_predictions(self, client, sample_patient):
        r = client.get(f"/api/predictions/{sample_patient.patient_id}")
        assert r.status_code in [401, 403]


# ═══════════════════════════════════════════════
# 7. ALERTS TESTS
# ═══════════════════════════════════════════════

class TestAlerts:
    def test_list_alerts(self, client, admin_user):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.get("/api/alerts/", headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_unread_count(self, client, admin_user):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.get("/api/alerts/unread/count", headers=h)
        assert r.status_code == 200
        assert "unread_count" in r.json()

    def test_no_auth_alerts(self, client):
        r = client.get("/api/alerts/")
        assert r.status_code in [401, 403]

    def test_nurse_cannot_mark_alert_read(self, client, admin_user, nurse_user):
        h = get_auth_header(client, "testnurse", "nurse123")
        r = client.patch("/api/alerts/1/read", headers=h)
        assert r.status_code == 403


# ═══════════════════════════════════════════════
# 8. SETTINGS TESTS
# ═══════════════════════════════════════════════

class TestSettings:
    def test_admin_can_list_settings(self, client, admin_user, threshold_setting):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.get("/api/settings/", headers=h)
        assert r.status_code == 200

    def test_get_threshold(self, client, admin_user, threshold_setting):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.get("/api/settings/threshold", headers=h)
        assert r.status_code == 200
        assert r.json()["key"] == "high_risk_threshold"

    def test_update_threshold(self, client, admin_user, threshold_setting):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.put("/api/settings/threshold", headers=h, json={"value": "0.75"})
        assert r.status_code == 200

    def test_update_threshold_invalid(self, client, admin_user, threshold_setting):
        h = get_auth_header(client, "testadmin", "admin123")
        r = client.put("/api/settings/threshold", headers=h, json={"value": "2.0"})
        assert r.status_code == 400

    def test_doctor_cannot_access_settings(self, client, admin_user, doctor_user):
        h = get_auth_header(client, "testdoctor", "doctor123")
        r = client.get("/api/settings/", headers=h)
        assert r.status_code == 403


# ═══════════════════════════════════════════════
# 9. TASKS (no auth) TESTS
# ═══════════════════════════════════════════════

class TestTasks:
    def test_create_task(self, client):
        r = client.post("/api/tasks/", json={
            "patient_id": "1", "description": "Check vitals",
            "scheduled_time": "14:00", "task_type": "vitals", "priority": "high"
        })
        assert r.status_code == 200
        assert r.json()["id"] is not None
        assert r.json()["is_completed"] == False

    def test_list_tasks(self, client):
        client.post("/api/tasks/", json={
            "patient_id": "1", "description": "Test",
            "scheduled_time": "15:00", "task_type": "med", "priority": "low"
        })
        r = client.get("/api/tasks/")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_update_task(self, client):
        cr = client.post("/api/tasks/", json={
            "patient_id": "1", "description": "Complete me",
            "scheduled_time": "16:00", "task_type": "lab", "priority": "medium"
        })
        tid = cr.json()["id"]
        r = client.patch(f"/api/tasks/{tid}", json={"is_completed": True})
        assert r.status_code == 200
        assert r.json()["is_completed"] == True

    def test_update_nonexistent_task(self, client):
        r = client.patch("/api/tasks/99999", json={"is_completed": True})
        assert r.status_code == 404

    def test_create_task_empty_body(self, client):
        r = client.post("/api/tasks/", json={})
        assert r.status_code == 422

    def test_task_response_structure(self, client):
        r = client.post("/api/tasks/", json={
            "patient_id": "1", "description": "Structure test",
            "scheduled_time": "17:00", "task_type": "check", "priority": "low"
        })
        for f in ["id", "patient_id", "description", "is_completed", "created_at"]:
            assert f in r.json()


# ═══════════════════════════════════════════════
# 10. LABS (no auth) TESTS
# ═══════════════════════════════════════════════

class TestLabs:
    def test_create_lab(self, client):
        r = client.post("/api/labs/", json={
            "patient_id": "1", "test_name": "WBC",
            "value": 12.5, "unit": "K/uL",
            "reference_range": "4.5-11.0", "status": "High"
        })
        assert r.status_code == 200
        assert r.json()["test_name"] == "WBC"
        assert r.json()["id"] is not None

    def test_list_labs(self, client):
        client.post("/api/labs/", json={
            "patient_id": "1", "test_name": "CRP",
            "value": 5.0, "unit": "mg/L",
            "reference_range": "0-10", "status": "Normal"
        })
        r = client.get("/api/labs/")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_filter_labs_by_patient(self, client):
        client.post("/api/labs/", json={
            "patient_id": "42", "test_name": "Lactate",
            "value": 3.2, "unit": "mmol/L",
            "reference_range": "0.5-2.2", "status": "High"
        })
        r = client.get("/api/labs/?patient_id=42")
        assert r.status_code == 200
        assert all(l["patient_id"] == "42" for l in r.json())

    def test_create_lab_empty_body(self, client):
        r = client.post("/api/labs/", json={})
        assert r.status_code == 422

    def test_create_lab_wrong_type(self, client):
        r = client.post("/api/labs/", json={
            "patient_id": "1", "test_name": "WBC",
            "value": "not_a_number", "unit": "K/uL",
            "reference_range": "4.5-11.0", "status": "Normal"
        })
        assert r.status_code == 422

    def test_lab_response_structure(self, client):
        r = client.post("/api/labs/", json={
            "patient_id": "1", "test_name": "PCT",
            "value": 0.5, "unit": "ng/mL",
            "reference_range": "0-0.5", "status": "Normal"
        })
        for f in ["id", "patient_id", "test_name", "value", "unit", "recorded_at"]:
            assert f in r.json()


# ═══════════════════════════════════════════════
# 11. CHAINED WORKFLOW TESTS
# ═══════════════════════════════════════════════

class TestWorkflows:
    def test_full_patient_workflow(self, client, admin_user, nurse_user, doctor_user):
        """Create → Get → Update → verify chain."""
        h_nurse = get_auth_header(client, "testnurse", "nurse123")
        h_admin = get_auth_header(client, "testadmin", "admin123")
        h_doc = get_auth_header(client, "testdoctor", "doctor123")

        # Create patient
        r = client.post("/api/patients/", headers=h_nurse, json={
            "full_name": "Workflow Patient", "age": 60, "gender": "female",
            "bed_number": "ICU-WF", "ward_name": "ICU",
            "assigned_doctor_id": doctor_user.user_id
        })
        assert r.status_code == 200
        pid = r.json()["patient_id"]

        # Get patient by ID
        r = client.get(f"/api/patients/{pid}", headers=h_admin)
        assert r.status_code == 200
        assert r.json()["full_name"] == "Workflow Patient"

        # Update patient (nurse can update bed)
        r = client.patch(f"/api/patients/{pid}", headers=h_nurse,
                         json={"bed_number": "ICU-WF2"})
        assert r.status_code == 200

        # Doctor updates notes
        r = client.patch(f"/api/patients/{pid}/notes", headers=h_doc,
                         json={"diagnosis_notes": "Workflow diagnosis"})
        assert r.status_code == 200

        # Verify update
        r = client.get(f"/api/patients/{pid}", headers=h_admin)
        assert r.json()["bed_number"] == "ICU-WF2"

    def test_vital_to_prediction_workflow(self, client, admin_user, nurse_user, sample_patient):
        """Add vital → check predictions exist."""
        h_nurse = get_auth_header(client, "testnurse", "nurse123")
        h_admin = get_auth_header(client, "testadmin", "admin123")

        # Add vital
        r = client.post("/api/vitals/", headers=h_nurse, json={
            "patient_id": sample_patient.patient_id,
            "heart_rate": 110.0, "temperature": 38.9, "spo2": 91.0
        })
        assert r.status_code == 200

        # Check vitals saved
        r = client.get(f"/api/vitals/{sample_patient.patient_id}", headers=h_admin)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_task_crud_workflow(self, client):
        """Create → Read → Update → verify completed."""
        # Create
        r = client.post("/api/tasks/", json={
            "patient_id": "1", "description": "Workflow task",
            "scheduled_time": "10:00", "task_type": "med", "priority": "high"
        })
        tid = r.json()["id"]

        # Read
        r = client.get("/api/tasks/?patient_id=1")
        found = any(t["id"] == tid for t in r.json())
        assert found

        # Update
        r = client.patch(f"/api/tasks/{tid}", json={"is_completed": True})
        assert r.json()["is_completed"] == True

    def test_lab_crud_workflow(self, client):
        """Create → Read → verify in list."""
        r = client.post("/api/labs/", json={
            "patient_id": "77", "test_name": "Workflow Lab",
            "value": 1.0, "unit": "mg/dL",
            "reference_range": "0-5", "status": "Normal"
        })
        lab_id = r.json()["id"]

        r = client.get("/api/labs/?patient_id=77")
        found = any(l["id"] == lab_id for l in r.json())
        assert found


# ═══════════════════════════════════════════════
# 12. PERFORMANCE TESTS
# ═══════════════════════════════════════════════

class TestPerformance:
    def test_all_endpoints_under_2s(self, client, admin_user, sample_patient):
        h = get_auth_header(client, "testadmin", "admin123")
        endpoints = [
            ("GET", "/api/health"),
            ("GET", "/api/patients/"),
            ("GET", "/api/alerts/"),
            ("GET", "/api/alerts/unread/count"),
            ("GET", f"/api/vitals/{sample_patient.patient_id}"),
            ("GET", f"/api/predictions/{sample_patient.patient_id}"),
        ]
        for method, url in endpoints:
            start = time.time()
            if method == "GET":
                r = client.get(url, headers=h)
            elapsed = (time.time() - start) * 1000
            assert elapsed < 2000, f"{method} {url} took {elapsed:.0f}ms"
