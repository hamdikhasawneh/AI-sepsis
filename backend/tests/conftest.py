"""
Pytest configuration and fixtures for the ICU Sepsis Detection System.

Uses an in-memory SQLite database for fast, isolated tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.security import hash_password
from app.models.user import User
from app.models.patient import Patient
from app.models.vital_signs import VitalSign
from app.models.prediction import Prediction
from app.models.alert import Alert
from app.models.system_setting import SystemSetting

# In-memory SQLite database for tests
SQLALCHEMY_TEST_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Get a test database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """Get a FastAPI test client with overridden DB dependency."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    user = User(
        username="testadmin",
        email="admin@test.com",
        password_hash=hash_password("admin123"),
        full_name="Test Admin",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def doctor_user(db):
    """Create and return a doctor user."""
    user = User(
        username="testdoctor",
        email="doctor@test.com",
        password_hash=hash_password("doctor123"),
        full_name="Dr. Test",
        role="doctor",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def nurse_user(db):
    """Create and return a nurse user."""
    user = User(
        username="testnurse",
        email="nurse@test.com",
        password_hash=hash_password("nurse123"),
        full_name="Nurse Test",
        role="nurse",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_patient(db, doctor_user, nurse_user):
    """Create and return a sample patient."""
    patient = Patient(
        full_name="Test Patient",
        age=55,
        gender="male",
        bed_number="ICU-01",
        ward_name="ICU",
        status="admitted",
        assigned_doctor_id=doctor_user.user_id,
        created_by_user_id=nurse_user.user_id,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@pytest.fixture
def threshold_setting(db, admin_user):
    """Create the default threshold setting."""
    setting = SystemSetting(
        key="high_risk_threshold",
        value="0.80",
        updated_by_user_id=admin_user.user_id,
    )
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def get_auth_header(client, username: str, password: str) -> dict:
    """Helper: Login and return authorization header."""
    resp = client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
