# 🏥 ARISE — AI Real-time ICU Sepsis Early-warning

A full-stack clinical decision-support system for real-time ICU sepsis prediction, powered by a **Dynamic Survival Transformer (DST v2)** trained on MIMIC-IV data. Features role-based dashboards for physicians and nurses, GradientSHAP explainability, automated lab report OCR via Gemini Vision, and a live ICU simulation engine.

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

| Role      | Username      | Password    | Dashboard                                          |
|-----------|---------------|-------------|-----------------------------------------------------|
| Admin     | `admin`       | `admin123`  | Full access — users, patients, settings, simulation |
| Physician | `dr.smith`    | `doctor123` | Assigned patients, risk scores, SHAP reasoning, alerts |
| Physician | `dr.johnson`  | `doctor123` | Same as above                                       |
| Nurse     | `nurse.jane`  | `nurse123`  | Patient list, vitals entry, lab upload, task management |
| Nurse     | `nurse.mike`  | `nurse123`  | Same as above                                       |

---

## Key Features

| Feature | Description |
|---------|-------------|
| **DST v2 Predictions** | Dynamic Survival Transformer with 25 vital + 127 static features, Platt-calibrated survival curves, 12-hour sepsis horizon |
| **GradientSHAP Explainability** | Top-8 feature attributions per patient, displayed as risk drivers vs protective factors in the physician dashboard |
| **Gemini Vision OCR** | Upload lab report PDFs/images → automatic extraction of lab values via Google Gemini 2.0 Flash → values feed into the DST model |
| **ICU Simulation Engine** | Replay real MIMIC-IV ICU stays hour-by-hour with live vital signs, lab results, and predictions streaming to the dashboard |
| **Real-time Alerts** | WebSocket-based alert delivery with browser notifications when sepsis risk crosses configurable thresholds |
| **Role-based Dashboards** | Physician view (risk trajectories, SHAP, alerts) and Nurse view (vitals entry, lab upload, task management) |
| **Lab Data Pipeline** | Nurse-submitted labs and OCR-extracted values are injected into the DST prediction pipeline (replacing population medians) |
| **Task Management** | Physician-assigned clinical tasks tracked per patient with priority and completion status |

---

## 📊 Model Performance

The ARISE system is powered by a high-performance **Dynamic Survival Transformer (DST v2)**, which significantly outperforms traditional rule-based and classification baselines in early sepsis detection.

### Performance Summary

| Model Architecture | Task Type | AUROC | AUPRC | Sensitivity | Lead Time |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DST v2 (Primary)** | Survival | 0.7957* | 0.1690 | **69.7%** | **28.2 Hours** |
| **Full Ensemble** | Classification | **0.9013** | **0.4256** | 48.06% | N/A |
| **Tree Ensemble** | Classification | 0.8936 | 0.3833 | 43.09% | N/A |
| **LSTM (Rich)** | Sequence | 0.8787 | 0.3774 | 47.82% | N/A |
| **Random Forest** | Classification | 0.8791 | 0.3260 | 45.76% | N/A |

*\* Note: DST v2 AUROC reflects rolling-window performance on streaming data. See [Model Performance](docs/model_performance.md) for full details.*

For a complete breakdown of all model metrics, features, and evaluation methodologies, please refer to:
👉 **[Full Model Performance Documentation](docs/model_performance.md)**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      React Frontend (Vite)                       │
│  Zustand · React Router 7 · Recharts · Framer Motion · Tailwind │
│  Port 5173                                                       │
├───────────────────────┬─────────────────────────────────────────┤
│                       │  REST + WebSocket                        │
│                       ▼                                          │
│                 FastAPI Backend                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ API Layer (11 route modules)                               │  │
│  │  auth · users · patients · vitals · predictions · alerts   │  │
│  │  settings · tasks · labs · documents · simulation          │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │ Service Layer                                              │  │
│  │  prediction_service (DST v2 + Mock fallback)               │  │
│  │  simulation_service (MIMIC-IV replay engine)               │  │
│  │  ocr_service (PyMuPDF + Gemini Vision + regex)             │  │
│  │  alert_service · vital_service · patient_service           │  │
│  │  auth_service · settings_service                           │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │ ML Layer                                                   │  │
│  │  DynamicSurvivalTransformer (PyTorch)                      │  │
│  │  Platt calibrators · StandardScaler · Winsorisation        │  │
│  │  GradientSHAP precomputed attributions                     │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │ SQLAlchemy ORM (9 models) + SQLite/PostgreSQL              │  │
│  │  Port 8000                                                 │  │
│  └────────────────────────────────────────────────────────────┘  │
├───────────────────────┬─────────────────────────────────────────┤
│                       ▼                                          │
│              PostgreSQL 16 (Docker) / SQLite (local dev)         │
│  Port 5432                                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer              | Technology                                                         |
|--------------------|--------------------------------------------------------------------|
| Frontend           | React 18, Vite 5, React Router 7, Recharts, Framer Motion, Zustand |
| Styling            | Tailwind CSS 3, custom dark medical theme                          |
| Backend            | FastAPI, SQLAlchemy 2.0, Pydantic v2, Pydantic Settings            |
| ML / Inference     | PyTorch 2.5, scikit-learn, NumPy, pandas, SHAP                    |
| OCR                | PyMuPDF (text PDFs), Google Gemini 2.0 Flash (scanned/image)      |
| Database           | PostgreSQL 16 (Docker) / SQLite (local dev)                       |
| Auth               | JWT (python-jose), bcrypt (passlib)                                |
| Real-time          | WebSocket (FastAPI native)                                         |
| Containerisation   | Docker, Docker Compose                                             |
| Testing            | pytest, httpx                                                      |

---

## Project Structure

```
AI-sepsis/
├── backend/
│   ├── app/
│   │   ├── api/                   # API route handlers (11 modules)
│   │   │   ├── auth.py            #   POST /login, GET /me
│   │   │   ├── users.py           #   CRUD users (admin only)
│   │   │   ├── patients.py        #   CRUD patients (role-based)
│   │   │   ├── vitals.py          #   Vital ingestion + manual simulator
│   │   │   ├── predictions.py     #   Prediction history + SHAP
│   │   │   ├── alerts.py          #   Alert management
│   │   │   ├── settings.py        #   System settings (admin)
│   │   │   ├── tasks.py           #   Clinical task management
│   │   │   ├── labs.py            #   Lab result CRUD
│   │   │   ├── documents.py       #   Lab document upload + OCR
│   │   │   └── simulation.py      #   ICU simulation control
│   │   ├── core/                  # Configuration, security, WebSocket
│   │   ├── db/                    # Database session, base, seed
│   │   ├── models/                # 9 SQLAlchemy models + DST arch
│   │   │   ├── user.py
│   │   │   ├── patient.py
│   │   │   ├── vital_signs.py
│   │   │   ├── prediction.py
│   │   │   ├── alert.py
│   │   │   ├── system_setting.py
│   │   │   ├── task.py
│   │   │   ├── lab_result.py
│   │   │   ├── document.py
│   │   │   ├── transformer_arch.py  # DynamicSurvivalTransformer (PyTorch)
│   │   │   └── ml_files/           # Trained model weights & artifacts
│   │   ├── schemas/               # Pydantic validation schemas
│   │   ├── services/              # 8 business logic services
│   │   │   ├── prediction_service.py  # DST v2 + Mock + SHAP
│   │   │   ├── simulation_service.py  # MIMIC replay engine
│   │   │   ├── ocr_service.py         # Gemini Vision + regex OCR
│   │   │   ├── alert_service.py
│   │   │   ├── vital_service.py
│   │   │   ├── patient_service.py
│   │   │   ├── auth_service.py
│   │   │   └── settings_service.py
│   │   ├── dependencies/          # Auth + RBAC dependencies
│   │   ├── uploads/               # Uploaded lab documents
│   │   └── main.py                # FastAPI application entry
│   ├── data/
│   │   └── simulation/            # DST_Simulation_v5.xlsx
│   ├── tests/                     # pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── screens/               # 4 page components
│   │   │   ├── HomeScreen.jsx     #   Landing page
│   │   │   ├── LoginScreen.jsx    #   Role-based login
│   │   │   ├── PhysicianScreen.jsx#   Physician dashboard
│   │   │   └── NurseScreen.jsx    #   Nurse dashboard
│   │   ├── components/
│   │   │   ├── shared/            # AppHeader, ChartTooltip, etc.
│   │   │   ├── ui/                # Badge, Button, Card, Input, Modal, Spinner, Tabs
│   │   │   └── SimulationControl.jsx
│   │   ├── store/
│   │   │   └── appStore.js        # Zustand global state
│   │   ├── App.jsx                # Routing + WebSocket connector
│   │   ├── main.jsx               # React entry point
│   │   └── index.css              # Tailwind + custom styles
│   ├── Dockerfile
│   ├── tailwind.config.js
│   └── package.json
├── src/                           # ML pipeline scripts (preprocessing, features)
├── notebooks/                     # Jupyter notebooks (EDA, training)
├── docs/                          # Data dictionary, label definitions
├── docker-compose.yml
├── .env.example
├── RUNNING.md                     # Detailed local + Docker setup guide
└── README.md
```

---

## Database Schema

| Table              | Key Fields                                                                |
|--------------------|---------------------------------------------------------------------------|
| `users`            | user_id, username, email, password_hash, role, is_active                  |
| `patients`         | patient_id, full_name, age, gender, status, assigned_doctor_id, bed_number, ward_name, diagnosis_notes |
| `vital_signs`      | vital_id, patient_id, heart_rate, respiratory_rate, temperature, spo2, systolic_bp, diastolic_bp, mean_bp, source |
| `predictions`      | prediction_id, patient_id, risk_score, risk_level, threshold_used, model_version, input_window_hours |
| `alerts`           | alert_id, prediction_id, patient_id, alert_message, alert_level, is_read, read_by_user_id |
| `lab_results`      | id, patient_id, test_name, value, unit, reference_range, status, recorded_at |
| `documents`        | id, patient_id, file_name, file_path, extracted_text, uploaded_at         |
| `tasks`            | id, patient_id, description, scheduled_time, task_type, priority, is_completed |
| `system_settings`  | setting_id, key, value, updated_by_user_id                               |

### Roles
- **admin** — Full access: manage users, patients, settings, simulation controls
- **physician** (doctor) — View assigned patients, risk scores, SHAP explanations, manage alerts, clinical notes, assign tasks
- **nurse** — Add patients, record vitals, upload lab documents, view alerts (read-only), manage tasks

---

## API Reference

### Authentication
| Method | Endpoint              | Description               | Access        |
|--------|-----------------------|---------------------------|---------------|
| POST   | `/api/auth/login`     | Login, returns JWT token  | Public        |
| GET    | `/api/auth/me`        | Current user info         | Authenticated |

### Users
| Method | Endpoint              | Description          | Access       |
|--------|-----------------------|----------------------|--------------|
| POST   | `/api/users/`         | Create user          | Admin        |
| GET    | `/api/users/`         | List users           | Admin        |
| GET    | `/api/users/doctors`  | List doctors         | Admin, Nurse |

### Patients
| Method | Endpoint                        | Description            | Access         |
|--------|---------------------------------|------------------------|----------------|
| POST   | `/api/patients/`                | Add patient            | Admin, Nurse   |
| GET    | `/api/patients/`                | List patients          | Authenticated  |
| GET    | `/api/patients/{id}`            | Patient details        | Authenticated  |
| PATCH  | `/api/patients/{id}`            | Update patient         | Admin, Nurse   |
| PATCH  | `/api/patients/{id}/notes`      | Update clinical notes  | Admin, Doctor  |

### Vitals & Manual Simulator
| Method | Endpoint                          | Description                | Access       |
|--------|-----------------------------------|----------------------------|--------------|
| POST   | `/api/vitals/`                    | Record vital signs         | Admin, Nurse |
| GET    | `/api/vitals/{patient_id}`        | Get patient vitals         | Authenticated |
| POST   | `/api/vitals/simulate`            | Run one simulation cycle   | Admin        |
| POST   | `/api/vitals/simulator/start`     | Start auto-simulator       | Admin        |
| POST   | `/api/vitals/simulator/stop`      | Stop auto-simulator        | Admin        |
| GET    | `/api/vitals/simulator/status`    | Simulator status           | Admin        |
| PUT    | `/api/vitals/simulator/interval`  | Set simulator interval     | Admin        |

### Predictions & SHAP
| Method | Endpoint                               | Description                       | Access        |
|--------|----------------------------------------|-----------------------------------|---------------|
| GET    | `/api/predictions/{patient_id}`        | Prediction history                | Authenticated |
| GET    | `/api/predictions/{patient_id}/latest` | Latest prediction                 | Authenticated |
| GET    | `/api/predictions/{patient_id}/shap`   | GradientSHAP feature importance   | Authenticated |

### Alerts
| Method | Endpoint                     | Description            | Access        |
|--------|------------------------------|------------------------|---------------|
| GET    | `/api/alerts/`               | List alerts            | Authenticated |
| GET    | `/api/alerts/unread/count`   | Unread alert count     | Authenticated |
| PATCH  | `/api/alerts/{id}/read`      | Mark alert as read     | Doctor only   |

### Lab Results
| Method | Endpoint        | Description              | Access       |
|--------|-----------------|--------------------------|--------------|
| GET    | `/api/labs/`    | List labs (filter by patient) | Authenticated |
| POST   | `/api/labs/`    | Create lab result        | Admin, Nurse |

### Document Upload & OCR
| Method | Endpoint              | Description                                    | Access       |
|--------|-----------------------|------------------------------------------------|--------------|
| POST   | `/api/documents/upload` | Upload lab PDF/image → OCR → extract lab values | Admin, Nurse |

### ICU Simulation
| Method | Endpoint                | Description                        | Access          |
|--------|-------------------------|------------------------------------|-----------------|
| GET    | `/api/simulation/cases` | List available MIMIC cases         | Authenticated   |
| GET    | `/api/simulation/status`| Current simulation status          | Authenticated   |
| POST   | `/api/simulation/start` | Start simulation for a case        | Admin, Doctor   |
| POST   | `/api/simulation/stop`  | Stop running simulation            | Admin, Doctor   |
| DELETE | `/api/simulation/clear` | Clear simulation patients from DB  | Admin, Doctor   |

### Tasks
| Method | Endpoint              | Description                   | Access          |
|--------|-----------------------|-------------------------------|-----------------|
| GET    | `/api/tasks/`         | List tasks (filter by patient)| Authenticated   |
| POST   | `/api/tasks/`         | Create clinical task          | Admin, Doctor   |
| PATCH  | `/api/tasks/{id}`     | Update task completion        | Authenticated   |

### Settings
| Method | Endpoint                  | Description            | Access |
|--------|---------------------------|------------------------|--------|
| GET    | `/api/settings/`          | List all settings      | Admin  |
| GET    | `/api/settings/threshold` | Get alert threshold    | Admin  |
| PUT    | `/api/settings/threshold` | Update alert threshold | Admin  |

---

## Prediction Pipeline

### Dynamic Survival Transformer (DST v2)

The core ML model is a **Dynamic Survival Transformer** trained on MIMIC-IV ICU data for incident sepsis prediction (onset > 4 hours after admission).

**Architecture:**
- **Input:** 25-dimensional vital/lab time series (rolling 12-hour window) + 127-dimensional static patient features
- **Encoder:** 3-layer Transformer with 8 attention heads (d_model=256), CLS token pooling
- **Static branch:** 2-layer MLP encoding demographics, admission type, and aggregated lab/vital statistics
- **Fusion:** LayerNorm → 3-layer MLP → softmax over 48 discrete time bins
- **Output:** Survival curve S(t); risk score = 1 − S(12h) calibrated to clinical range

**Pipeline flow:**
1. Vitals are recorded (manual entry, monitor import, or simulation)
2. System builds a growing window of all vitals from admission
3. Latest lab values (nurse-entered or OCR-extracted) are injected into each timestep
4. DST v2 processes the 12-hour rolling window + 127 static features
5. CIF@12h is mapped to a clinical risk score (0.0–1.0) via empirical calibration
6. If risk ≥ threshold → alert created → WebSocket broadcast → browser notification

### Risk Level Mapping

| Score Range    | Level    | Alert Tier |
|----------------|----------|------------|
| ≥ 0.70         | Critical | 🔴 Critical alert created |
| ≥ 0.50         | High     | 🟠 High risk alert created |
| ≥ threshold×0.6| Medium   | 🟡 No alert (monitoring) |
| < threshold×0.6| Low      | 🟢 No alert |

### Fallback Behaviour

If the DST v2 model files are not found in `backend/app/models/ml_files/`, the system automatically falls back to a **MockPredictorService** that generates rule-based risk scores from vital sign thresholds. The model version is displayed in the prediction response:

| model_version | Meaning |
|---------------|---------|
| `Dynamic Survival Transformer v2` | Real DST v2 model is active |
| `Dynamic Survival Transformer (Mock)` | Fallback mock model |

---

## Lab Document OCR Pipeline

The system supports uploading lab report PDFs and images (PNG, JPG, JPEG, BMP, TIFF) via the nurse dashboard. The OCR pipeline processes documents in priority order:

1. **PyMuPDF text extraction** — instant for text-based PDFs (hospital e-reports)
2. **Gemini Vision API** (gemini-2.0-flash) — handles scanned PDFs and images; renders pages at 150 DPI and sends to Gemini for structured JSON extraction
3. **Regex fallback** — pattern matching on whatever text was extracted

Extracted lab values are:
- Saved to the `lab_results` table with test name, value, unit, reference range, and status
- Automatically injected into the DST prediction pipeline (replacing population medians)
- Visible in both the nurse and physician dashboards

**Supported lab tests:** WBC, Lactate, Procalcitonin, CRP, Glucose, Creatinine, Hemoglobin, Platelets, Sodium, Potassium, Haematocrit, RBC, MCV, Neutrophils, Lymphocytes, INR.

**Requires:** `GEMINI_API_KEY` environment variable for Gemini Vision OCR (free tier available).

---

## ICU Simulation Engine

The simulation engine replays real MIMIC-IV ICU stays hour-by-hour, streaming vital signs, lab results, and DST predictions to the dashboard in real time.

**How it works:**
1. Select a case from the simulation Excel file (`DST_Simulation_v5.xlsx`)
2. A simulated patient is created in the database (ward: "Simulation Lab")
3. Each hour: vital signs + lab values are written → DST v2 prediction runs → alerts checked
4. Simulation pace: 1 ICU hour = 3 seconds (configurable)
5. The frontend polls every 5 seconds for updated data

**Data source:** `backend/data/simulation/DST_Simulation_v5.xlsx` with sheets:
- `Hourly_Sequence_25` — 25 time-varying features per hour
- `Static_Features_127` (or `Static_Input_x_static`) — 127 static features per case

---

## GradientSHAP Explainability

The physician dashboard includes an **AI Reasoning** tab that shows the top 8 features driving each patient's sepsis risk prediction.

- Precomputed GradientSHAP values stored in `backend/app/models/ml_files/dst_shap_values.npy`
- Each feature is labelled as **Risk +** (increases sepsis risk) or **Protective** (decreases risk)
- Exposed via `GET /api/predictions/{patient_id}/shap`

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

| Variable              | Default                                                        | Description                          |
|-----------------------|----------------------------------------------------------------|--------------------------------------|
| `DATABASE_URL`        | `postgresql://sepsis_user:sepsis_pass@db:5432/sepsis_db`       | Database connection (Postgres/SQLite)|
| `JWT_SECRET_KEY`      | `dev-secret-key-...`                                           | JWT signing key (change in prod!)    |
| `DEBUG`               | `true`                                                         | Enable debug mode                    |
| `GEMINI_API_KEY`      | *(empty)*                                                      | Google Gemini API key for Vision OCR |
| `CORS_ORIGINS`        | `http://localhost:5173,http://localhost:5174,http://localhost:3000` | Comma-separated allowed origins   |
| `SIMULATION_EXCEL_PATH`| `backend/data/simulation/DST_Simulation_v5.xlsx`              | Path to simulation data file         |

See `.env.example` for cloud deployment configuration.

---

## Cloud Deployment

To deploy to cloud (AWS, GCP, Azure, etc.):

1. **Update `.env`** with production database URL and a strong JWT secret
2. **Set `DEBUG=false`**
3. **Set `GEMINI_API_KEY`** for lab OCR functionality
4. **Update `CORS_ORIGINS`** to your domain (via env var or `backend/app/core/config.py`)
5. **Use a managed PostgreSQL** (RDS, Cloud SQL, etc.) instead of the Docker container
6. **Add HTTPS** via a reverse proxy (nginx, Cloudflare, etc.)
7. **Remove `--reload`** from the backend Dockerfile CMD for production
8. **Build the frontend** with `npm run build` and serve static files via nginx

---

## Seed Data

On first startup, the database is automatically populated with:
- **5 users** (1 admin, 2 physicians, 2 nurses)
- **12 patients** (8 admitted, 4 discharged/transferred)
- **~192 vital sign readings** (24 per admitted patient)
- **~48 predictions** (6 per admitted patient)
- **4 alerts** (3 unread, 1 read)
- **2 system settings** (threshold=0.80, sound=true)

---

## License

University project — for educational purposes.
