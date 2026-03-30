"""Tests for authentication endpoints and role-based access control."""

from tests.conftest import get_auth_header


class TestAuthLogin:
    """Test POST /api/auth/login."""

    def test_login_valid_admin(self, client, admin_user):
        resp = client.post("/api/auth/login", json={
            "username": "testadmin",
            "password": "admin123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"]
        assert data["role"] == "admin"
        assert data["username"] == "testadmin"

    def test_login_valid_doctor(self, client, doctor_user):
        resp = client.post("/api/auth/login", json={
            "username": "testdoctor",
            "password": "doctor123",
        })
        assert resp.status_code == 200
        assert resp.json()["role"] == "doctor"

    def test_login_wrong_password(self, client, admin_user):
        resp = client.post("/api/auth/login", json={
            "username": "testadmin",
            "password": "wrong",
        })
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/api/auth/login", json={
            "username": "nobody",
            "password": "xxx",
        })
        assert resp.status_code == 401

    def test_login_by_email(self, client, admin_user):
        resp = client.post("/api/auth/login", json={
            "username": "admin@test.com",
            "password": "admin123",
        })
        assert resp.status_code == 200
        assert resp.json()["username"] == "testadmin"


class TestAuthMe:
    """Test GET /api/auth/me."""

    def test_me_authenticated(self, client, admin_user):
        headers = get_auth_header(client, "testadmin", "admin123")
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "testadmin"

    def test_me_no_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 403

    def test_me_invalid_token(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer fake-token"})
        assert resp.status_code == 401


class TestRoleAccess:
    """Test role-based access control."""

    def test_admin_can_create_user(self, client, admin_user):
        headers = get_auth_header(client, "testadmin", "admin123")
        resp = client.post("/api/users/", headers=headers, json={
            "username": "newuser",
            "email": "new@test.com",
            "password": "pass123",
            "full_name": "New User",
            "role": "nurse",
        })
        assert resp.status_code == 200

    def test_nurse_cannot_create_user(self, client, nurse_user):
        headers = get_auth_header(client, "testnurse", "nurse123")
        resp = client.post("/api/users/", headers=headers, json={
            "username": "newuser",
            "email": "new@test.com",
            "password": "pass123",
            "full_name": "New User",
            "role": "nurse",
        })
        assert resp.status_code == 403

    def test_doctor_cannot_create_user(self, client, doctor_user):
        headers = get_auth_header(client, "testdoctor", "doctor123")
        resp = client.post("/api/users/", headers=headers, json={
            "username": "newuser",
            "email": "new@test.com",
            "password": "pass123",
            "full_name": "New User",
            "role": "nurse",
        })
        assert resp.status_code == 403
