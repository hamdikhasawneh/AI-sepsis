# 🏥 ICU Sepsis Early Warning Detection System

A full-stack web application for real-time ICU sepsis early detection, featuring role-based dashboards for doctors, nurses, and administrators.

> **Built for university demonstration purposes.** Includes a mock prediction service designed to be swapped with a real PyTorch LSTM model.

---

## Quick Start

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd AI-sepsis

# 2. Run with Docker Compose
docker compose up --build

# 3. Open the application
# Frontend:  http://localhost:5173
# API Docs:  http://localhost:8000/docs
# API:       http://localhost:8000/api/health
```

### Demo Accounts

| Role   | Username      | Password    | What They See                                     |
|--------|---------------|-------------|----------------------------------------------------|
| Admin  | `admin`       | `admin123`  | All patients, users, settings, simulator controls  |
| Doctor | `dr.smith`    | `doctor123` | Assigned patients, alerts, mark alerts as read     |
| Doctor | `dr.johnson`  | `doctor123` | Assigned patients, alerts, update clinical notes   |
| Nurse  | `nurse.jane`  | `nurse123`  | Patient list, record vitals, view alerts (readonly)|
| Nurse  | `nurse.mike`  | `nurse123`  | Same as nurse.jane                                 |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    React Frontend                    │
│  (Vite + React Router + Recharts + Axios)            │
│  Port 5173                                           │
├──────────────────────┬──────────────────────────────┤
│                      │ REST API (JSON)               │
│                      ▼                               │
│              FastAPI Backend                          │
│  ┌──────────┬──────────┬──────────┬──────────┐       │
│  │ Auth API │ Patient  │ Vitals   │ Alerts   │       │
│  │          │ API      │ API      │ API      │       │
│  ├──────────┴──────────┴──────────┴──────────┤       │
│  │           Service Layer                    │       │
│  │  auth_service | patient_service            │       │
│  │  vital_service | prediction_service        │       │
│  │  alert_service | settings_service          │       │
│  ├────────────────────────────────────────────┤       │
│  │  Mock Predictor ← (swap for real model)    │       │
│  ├────────────────────────────────────────────┤       │
│  │         SQLAlchemy ORM + Models            │       │
│  │  Port 8000                                 │       │
├──────────────────────┬───────────────────────┤       │
│                      ▼                               │
│              PostgreSQL 16                           │
│  Port 5432                                           │
└─────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer         | Technology                                       |
|---------------|--------------------------------------------------|
| Frontend      | React 18, Vite, React Router 6, Recharts, Axios  |
| Backend       | FastAPI, SQLAlchemy 2.0, Pydantic v2              |
| Database      | PostgreSQL 16                                     |
| Auth          | JWT (python-jose), bcrypt (passlib)               |
| Containerization | Docker, Docker Compose                         |
| Testing       | pytest, httpx, TestClient                         |

---

## Project Structure

```
AI-sepsis/
├── backend/
│   ├── app/
│   │   ├── api/              # API route handlers (7 modules)
│   │   │   ├── auth.py       #   POST /login, GET /me
│   │   │   ├── users.py      #   CRUD users (admin only)
│   │   │   ├── patients.py   #   CRUD patients (role-based)
│   │   │   ├── vitals.py     #   Vital ingestion + simulator
│   │   │   ├── predictions.py#   Prediction history
│   │   │   ├── alerts.py     #   Alert management
│   │   │   └── settings.py   #   System settings (admin)
│   │   ├── core/             # Configuration + security
│   │   ├── db/               # Database session, base, seed
│   │   ├── models/           # 6 SQLAlchemy models
│   │   ├── schemas/          # Pydantic validation schemas
│   │   ├── services/         # 6 business logic services
│   │   ├── dependencies/     # Auth + RBAC dependencies
│   │   └── main.py           # FastAPI application entry
│   ├── tests/                # pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/              # Axios client with JWT interceptors
│   │   ├── components/       # Navbar, ToastNotification
│   │   ├── context/          # AuthContext (global auth state)
│   │   ├── hooks/            # useNotificationSound
│   │   ├── pages/            # 10 page components
│   │   ├── routes/           # ProtectedRoute (RBAC)
│   │   ├── App.jsx           # Main routing
│   │   ├── main.jsx          # Entry point
│   │   └── index.css         # Dark medical theme (1300+ lines)
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Database Schema

| Table            | Key Fields                                      |
|------------------|-------------------------------------------------|
| `users`          | user_id, username, email, password_hash, role, is_active |
| `patients`       | patient_id, full_name, age, gender, status, assigned_doctor_id, bed_number, ward_name |
| `vital_signs`    | vital_id, patient_id, heart_rate, respiratory_rate, temperature, spo2, systolic_bp, diastolic_bp, mean_bp, source |
| `predictions`    | prediction_id, patient_id, risk_score, risk_level, threshold_used, model_version |
| `alerts`         | alert_id, prediction_id, patient_id, alert_message, alert_level, is_read, read_by_user_id |
| `system_settings`| setting_id, key, value, updated_by_user_id      |

### Roles
- **admin** — Full access: manage users, patients, settings, simulator
- **doctor** — View assigned patients, manage alerts (mark as read), update clinical notes
- **nurse** — Add patients, record vitals, view alerts (read-only)

---

## API Reference

### Authentication
| Method | Endpoint              | Description               | Access        |
|--------|-----------------------|---------------------------|---------------|
| POST   | `/api/auth/login`     | Login, returns JWT token  | Public        |
| GET    | `/api/auth/me`        | Current user info         | Authenticated |

### Users
| Method | Endpoint              | Description          | Access |
|--------|-----------------------|----------------------|--------|
| POST   | `/api/users/`         | Create user          | Admin  |
| GET    | `/api/users/`         | List users           | Admin  |
| GET    | `/api/users/doctors`  | List doctors         | Admin, Nurse |

### Patients
| Method | Endpoint                        | Description            | Access         |
|--------|---------------------------------|------------------------|----------------|
| POST   | `/api/patients/`                | Add patient            | Admin, Nurse   |
| GET    | `/api/patients/`                | List patients          | Authenticated  |
| GET    | `/api/patients/{id}`            | Patient details        | Authenticated  |
| PATCH  | `/api/patients/{id}`            | Update patient         | Admin, Nurse   |
| PATCH  | `/api/patients/{id}/notes`      | Update clinical notes  | Admin, Doctor  |

### Vitals & Simulator
| Method | Endpoint                        | Description                | Access |
|--------|---------------------------------|----------------------------|--------|
| POST   | `/api/vitals/`                  | Record vital signs         | Admin, Nurse |
| GET    | `/api/vitals/{patient_id}`      | Get patient vitals         | Authenticated |
| POST   | `/api/vitals/simulate`          | Run one simulation cycle   | Admin |
| POST   | `/api/vitals/simulator/start`   | Start auto-simulator       | Admin |
| POST   | `/api/vitals/simulator/stop`    | Stop auto-simulator        | Admin |
| GET    | `/api/vitals/simulator/status`  | Simulator status           | Admin |
| PUT    | `/api/vitals/simulator/interval`| Set simulator interval     | Admin |

### Predictions
| Method | Endpoint                            | Description              | Access        |
|--------|-------------------------------------|--------------------------|---------------|
| GET    | `/api/predictions/{patient_id}`     | Prediction history       | Authenticated |
| GET    | `/api/predictions/{patient_id}/latest` | Latest prediction     | Authenticated |

### Alerts
| Method | Endpoint                     | Description            | Access        |
|--------|------------------------------|------------------------|---------------|
| GET    | `/api/alerts/`               | List alerts            | Authenticated |
| GET    | `/api/alerts/unread/count`   | Unread alert count     | Authenticated |
| PATCH  | `/api/alerts/{id}/read`      | Mark alert as read     | Doctor only   |

### Settings
| Method | Endpoint                  | Description            | Access |
|--------|---------------------------|------------------------|--------|
| GET    | `/api/settings/`          | List all settings      | Admin  |
| GET    | `/api/settings/threshold` | Get alert threshold    | Admin  |
| PUT    | `/api/settings/threshold` | Update alert threshold | Admin  |

---

## Prediction Pipeline

### How It Works
1. Vital signs are recorded (manual entry or simulator)
2. System fetches the patient's last **6 hours** of vitals
3. Mock predictor analyzes vital patterns and generates a **risk score (0.0–1.0)**
4. If risk score ≥ threshold (default 80%), an **alert** is created
5. **Duplicate prevention**: No new unread alert if one already exists for the patient

### Risk Level Mapping
| Score Range        | Level    | Color  |
|--------------------|----------|--------|
| ≥ 0.90             | Critical | 🔴 Red |
| ≥ threshold (0.80) | High     | 🟠 Orange |
| ≥ threshold × 0.6  | Medium   | 🟡 Yellow |
| < threshold × 0.6  | Low      | 🟢 Green |

### Replacing the Mock Predictor with a Real Model

The prediction service uses an **abstract interface** (`BasePredictorService`) that makes model replacement straightforward:

**File:** `backend/app/services/prediction_service.py`

```python
# 1. Create your real predictor class
class RealPredictorService(BasePredictorService):
    def __init__(self):
        import torch
        self.model = torch.load("path/to/sepsis_model.pt")
        self.model.eval()

    def predict(self, vitals_window: list[dict]) -> float:
        # Convert vitals_window to tensor
        # Run inference
        # Return float between 0.0 and 1.0
        tensor = self._prepare_input(vitals_window)
        with torch.no_grad():
            output = self.model(tensor)
        return float(output.item())

# 2. Update the get_predictor function
def get_predictor() -> BasePredictorService:
    return RealPredictorService()  # <-- Change this line
```

The `predict()` method receives a list of dicts with keys: `heart_rate`, `respiratory_rate`, `temperature`, `spo2`, `systolic_bp`, `diastolic_bp`, `mean_bp`.

---

## Running Tests

```bash
# From the backend directory (inside container or locally)
cd backend
pytest tests/ -v

# Or run specific test files
pytest tests/test_auth.py -v
pytest tests/test_patients.py -v
pytest tests/test_vitals_predictions_alerts.py -v
```

---

## Environment Variables

| Variable        | Default                                | Description                |
|-----------------|----------------------------------------|----------------------------|
| `DATABASE_URL`  | `postgresql://sepsis_user:sepsis_pass@db:5432/sepsis_db` | PostgreSQL connection string |
| `JWT_SECRET_KEY`| `dev-secret-key-...`                   | JWT signing key (change in prod!) |
| `DEBUG`         | `true`                                 | Enable debug mode          |

See `.env.example` for cloud deployment configuration.

---

## Cloud Deployment

To deploy to cloud (AWS, GCP, Azure, etc.):

1. **Update `.env`** with production database URL and a strong JWT secret
2. **Set `DEBUG=false`**
3. **Update `CORS_ORIGINS`** in `backend/app/core/config.py` to your domain
4. **Use a managed PostgreSQL** (RDS, Cloud SQL, etc.) instead of the Docker container
5. **Add HTTPS** via a reverse proxy (nginx, Cloudflare, etc.)
6. **Remove `--reload`** from the backend Dockerfile CMD for production
7. **Build the frontend** with `npm run build` and serve static files via nginx

---

## Seed Data

On first startup, the database is automatically populated with:
- **5 users** (1 admin, 2 doctors, 2 nurses)
- **12 patients** (8 admitted, 4 discharged/transferred)
- **192 vital sign readings** (24 per admitted patient)
- **48 predictions** (6 per admitted patient)
- **4 alerts** (3 unread, 1 read)
- **2 system settings** (threshold=0.80, sound=true)

---

## License

University project — for educational purposes.
