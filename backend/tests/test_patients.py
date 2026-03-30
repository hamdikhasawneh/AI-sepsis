"""Tests for patient API endpoints and role-based permissions."""

from tests.conftest import get_auth_header


class TestPatientCRUD:
    """Test patient management."""

    def test_nurse_can_create_patient(self, client, nurse_user, doctor_user):
        headers = get_auth_header(client, "testnurse", "nurse123")
        resp = client.post("/api/patients/", headers=headers, json={
            "full_name": "New Patient",
            "age": 45,
            "gender": "female",
            "bed_number": "ICU-02",
            "ward_name": "ICU",
            "assigned_doctor_id": doctor_user.user_id,
        })
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "New Patient"
        assert resp.json()["status"] == "admitted"

    def test_admin_can_create_patient(self, client, admin_user, doctor_user):
        headers = get_auth_header(client, "testadmin", "admin123")
        resp = client.post("/api/patients/", headers=headers, json={
            "full_name": "Admin Patient",
            "age": 60,
            "gender": "male",
        })
        assert resp.status_code == 200

    def test_doctor_cannot_create_patient(self, client, doctor_user):
        headers = get_auth_header(client, "testdoctor", "doctor123")
        resp = client.post("/api/patients/", headers=headers, json={
            "full_name": "Doc Patient",
            "age": 50,
            "gender": "male",
        })
        assert resp.status_code == 403

    def test_list_patients(self, client, admin_user, sample_patient):
        headers = get_auth_header(client, "testadmin", "admin123")
        resp = client.get("/api/patients/", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_patient_detail(self, client, admin_user, sample_patient):
        headers = get_auth_header(client, "testadmin", "admin123")
        resp = client.get(f"/api/patients/{sample_patient.patient_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Test Patient"
        assert data["bed_number"] == "ICU-01"

    def test_doctor_can_update_notes(self, client, doctor_user, sample_patient):
        headers = get_auth_header(client, "testdoctor", "doctor123")
        resp = client.patch(
            f"/api/patients/{sample_patient.patient_id}/notes",
            headers=headers,
            json={"diagnosis_notes": "Updated diagnosis notes"},
        )
        assert resp.status_code == 200

    def test_nurse_can_update_patient(self, client, nurse_user, sample_patient, doctor_user):
        headers = get_auth_header(client, "testnurse", "nurse123")
        resp = client.patch(
            f"/api/patients/{sample_patient.patient_id}",
            headers=headers,
            json={"status": "discharged"},
        )
        assert resp.status_code == 200


class TestPatientFilters:
    """Test patient listing with filters."""

    def test_filter_active_patients(self, client, admin_user, sample_patient):
        headers = get_auth_header(client, "testadmin", "admin123")
        resp = client.get("/api/patients/", headers=headers, params={"status_filter": "active"})
        assert resp.status_code == 200
        for p in resp.json():
            assert p["status"] == "admitted"
